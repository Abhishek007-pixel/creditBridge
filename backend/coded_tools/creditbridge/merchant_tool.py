"""
MerchantScoringTool — Neuro SAN CodedTool
Redesigned to support:
1. GSTN-primary track: Filings regularity, customer diversity, sales volume stability.
2. Trade references-secondary track: Average duration, verification rate, officer ratings.
3. Optional status: returns status="not_available" if no data is found to enable weight redistribution.
"""
import os
import sys
import logging
from typing import Any, Union

_this_dir = os.path.dirname(os.path.abspath(__file__))
for _levels_up in (3, 4):
    _candidate = os.path.abspath(os.path.join(_this_dir, *(['..'] * _levels_up)))
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_merchant

logger = logging.getLogger(__name__)


def _synthetic_fallback(applicant_id: str) -> dict:
    try:
        data = generate_applicant_data(applicant_id)
        merchant_data = data["merchant"]
        score, reason = score_merchant(merchant_data)
        if score < 0:
            return {
                "source": "merchant",
                "applicant_id": applicant_id,
                "score": -1,
                "preliminary_score": -1,
                "status": "not_available",
                "reason": reason + " (synthetic fallback — no merchant data)",
                "preliminary_reason": reason + " (synthetic fallback — no merchant data)",
                "data_source": "synthetic"
            }
        return {
            "source": "merchant",
            "applicant_id": applicant_id,
            "score": score,
            "preliminary_score": score,
            "reason": reason + " (synthetic fallback)",
            "preliminary_reason": reason + " (synthetic fallback)",
            "raw_data": merchant_data,
            "data_source": "synthetic",
            "status": "success"
        }
    except Exception as e:
        return {
            "source": "merchant",
            "applicant_id": applicant_id,
            "score": 50,
            "preliminary_score": 50,
            "reason": f"Fallback error: {str(e)[:80]}",
            "preliminary_reason": f"Fallback error: {str(e)[:80]}",
            "data_source": "error",
            "status": "error"
        }


class MerchantScoringTool(CodedTool):
    """
    Evaluates business commercial reputational signals based on GSTN filings or verified trade references.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "merchant",
                "error": "No applicant_id provided",
                "score": -1,
                "status": "error",
                "reason": "Missing applicant ID",
            }

        try:
            from database_mongo import is_mongo_available, get_mongo_db
            
            if not is_mongo_available():
                return _synthetic_fallback(applicant_id)

            db = get_mongo_db()

            # ── TRACK A: GSTN PORTAL/FILE CHECK ──────────────────────────────
            gst_doc = await db.gstn_filings.find_one({
                "applicant_id": applicant_id,
                "stage": "scored"
            })

            if gst_doc:
                filing_history = gst_doc.get("filing_history", [])
                invoices = gst_doc.get("invoices", [])
                gstin = gst_doc.get("gstin", "Unknown GSTIN")
                business_name = gst_doc.get("business_name", "Registered MSME")

                # 1. Filing compliance (40 pts max)
                if filing_history:
                    on_time_count = sum(1 for f in filing_history if f.get("filed_on_time") is True)
                    filing_score = (on_time_count / len(filing_history)) * 40
                else:
                    on_time_count = 0
                    filing_score = 0

                # 2. Customer diversity (30 pts max)
                unique_buyers = len(set(inv.get("recipient_gstin") for inv in invoices if inv.get("recipient_gstin")))
                diversity_score = min(30, unique_buyers * 6)  # 5+ buyers = 30 pts

                # 3. Invoice volume stability (30 pts max)
                amounts = [float(inv.get("amount") or 0.0) for inv in invoices]
                total_amount = sum(amounts)
                if len(amounts) >= 3:
                    mean = total_amount / len(amounts)
                    variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
                    std_dev = variance ** 0.5
                    cv = std_dev / mean if mean > 0 else 0
                    if cv < 0.3:
                        stability_score = 30
                    elif cv < 0.6:
                        stability_score = 20
                    else:
                        stability_score = 10
                else:
                    stability_score = 20  # Default baseline for small history

                final_score = min(100, max(0, filing_score + diversity_score + stability_score))
                reason = (
                    f"GSTN verified ({business_name} / {gstin}): filed {on_time_count}/{len(filing_history)} returns on time. "
                    f"Active with {unique_buyers} buyer(s). Total verified turnover ₹{total_amount:,.0f}."
                )

                return {
                    "source": "merchant",
                    "applicant_id": applicant_id,
                    "score": final_score,
                    "preliminary_score": final_score,
                    "reason": reason,
                    "preliminary_reason": reason,
                    "metrics": {
                        "track": "gstn",
                        "gstin": gstin,
                        "business_name": business_name,
                        "filing_compliance_pct": round((on_time_count / len(filing_history)) * 100) if filing_history else 0,
                        "unique_buyers_count": unique_buyers,
                        "total_turnover": total_amount
                    },
                    "data_source": "mongodb",
                    "status": "success"
                }

            # ── TRACK B: OFFLINE PEER/TRADE REFERENCES CHECK ──────────────────
            cursor = db.merchant_references.find({"applicant_id": applicant_id})
            references = []
            async for doc in cursor:
                references.append(doc)

            if not references:
                # No GSTN and no references -> dynamic opt-out / weight redistribution
                return {
                    "source": "merchant",
                    "applicant_id": applicant_id,
                    "score": -1,
                    "preliminary_score": -1,
                    "status": "not_available",
                    "reason": "No GSTN filings or trade references uploaded. Merchant agent skipped.",
                    "preliminary_reason": "No GSTN filings or trade references uploaded. Merchant agent skipped.",
                    "data_source": "mongodb"
                }

            total_count = len(references)
            verified_refs = [r for r in references if r.get("verified_status") == "verified"]
            verified_count = len(verified_refs)

            # 1. Longevity score (40 pts max)
            durations = [float(r.get("duration_months") or 0.0) for r in references]
            avg_duration = sum(durations) / len(durations) if durations else 0
            if avg_duration >= 36:
                longevity_score = 40
            elif avg_duration >= 12:
                longevity_score = 20
            else:
                longevity_score = 10

            # 2. Verification status rate (30 pts max)
            verification_rate = verified_count / total_count if total_count > 0 else 0
            verification_score = verification_rate * 30

            # 3. Trade Rating Score (30 pts max)
            ratings = [float(r.get("rating") or 0.0) for r in verified_refs]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            rating_score = (avg_rating / 5.0) * 30

            final_score = min(100, max(0, longevity_score + verification_score + rating_score))
            reason = (
                f"Trade references: {verified_count}/{total_count} verified. "
                f"Avg relationship longevity: {avg_duration:.1f} months. Avg trade rating: {avg_rating:.1f}/5.0."
            )

            return {
                "source": "merchant",
                "applicant_id": applicant_id,
                "score": final_score,
                "preliminary_score": final_score,
                "reason": reason,
                "preliminary_reason": reason,
                "metrics": {
                    "track": "references",
                    "references_total": total_count,
                    "references_verified": verified_count,
                    "average_relationship_months": round(avg_duration, 1),
                    "average_rating": round(avg_rating, 2)
                },
                "data_source": "mongodb",
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error in MerchantScoringTool: {e}")
            fallback = _synthetic_fallback(applicant_id)
            fallback["tool_error"] = str(e)[:150]
            return fallback
