"""
Bill Consistency Scored Tool — Neuro SAN CodedTool
Replaces PhoneBillScoringTool.

Reads pre-processed bill data from MongoDB bill_documents collection,
computes consistency scores per stream, returns structured data for
the bill_consistency_agent to score.

If MongoDB is unavailable or applicant has no bills uploaded,
falls back to a synthetic baseline so the pipeline never breaks.
"""
import os
import sys
import asyncio
from typing import Any, Union

# Add backend root to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
for _levels_up in (3, 4):
    _candidate = os.path.abspath(os.path.join(_this_dir, *(['..'] * _levels_up)))
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from neuro_san.interfaces.coded_tool import CodedTool


# ── Bill type weights (from POV document) ────────────────────────────────
BILL_TYPE_WEIGHTS = {
    "rent_receipt":       1.5,
    "emi_receipt":        1.4,
    "school_fees":        1.3,
    "municipal_tax":      1.2,
    "insurance_premium":  1.1,
    "electricity":        1.0,
    "water":              0.9,
    "gas":                0.9,
    "phone":              0.7,
}

VERIFICATION_BONUS = {
    "bank_statement":     10,
    "account_aggregator": 10,
    "document_uploaded":  5,
    "image_uploaded":     3,
    "self_reported":      0,
}


def _amount_signal(amount_inr: float) -> float:
    if amount_inr < 500:    return 0.3
    if amount_inr < 3000:   return 0.6
    if amount_inr < 10000:  return 0.9
    return 1.0


def _compute_stream_score(
    bill_type: str,
    months_covered: int,
    avg_amount: float,
    verification_level: str,
    num_gaps: int = 0,
) -> int:
    """
    Compute 0-100 score for one bill stream (one bill_type + payee combo).
    Formula from BILL_AGENT_POV.md:
      stream_score = type_weight*0.35 + consistency*0.40 + amount*0.15 + verification*0.10
    """
    type_w      = BILL_TYPE_WEIGHTS.get(bill_type, 1.0)
    consistency = min(months_covered / 12.0, 1.0) - (num_gaps * 0.05)
    consistency = max(0.0, consistency)
    amt_sig     = _amount_signal(avg_amount)
    ver_bonus   = VERIFICATION_BONUS.get(verification_level, 0) / 10.0  # → 0.0–1.0

    raw = (type_w * 0.35) + (consistency * 0.40) + (amt_sig * 0.15) + (ver_bonus * 0.10)
    # Normalize: max raw ≈ 1.5*0.35 + 1.0*0.40 + 1.0*0.15 + 1.0*0.10 = 1.175
    normalized = raw / 1.175
    return min(100, max(0, round(normalized * 100)))


def _compute_final_bill_score(streams: list) -> tuple[int, str]:
    """
    Aggregate all streams into one final bill_consistency score (0-100).
    Diversity bonus: 1+ bill types adds up to 20% bonus.
    """
    if not streams:
        return 45, "No bills uploaded — using baseline score"

    scores = [s["stream_score"] for s in streams]
    unique_types = len(set(s["bill_type"] for s in streams))

    # Diversity multiplier: 1.0 for 1 type, up to 1.2 for 3+ types
    diversity = min(1.0 + (unique_types - 1) * 0.1, 1.2)
    avg = sum(scores) / len(scores)
    final = min(100, round(avg * diversity))

    # Build reason string
    top = sorted(streams, key=lambda s: s["stream_score"], reverse=True)
    top_name = top[0]["bill_type"].replace("_", " ").title() if top else "bill"
    reason = (
        f"{len(streams)} bill stream(s) across {unique_types} type(s). "
        f"Top: {top_name} — {top[0]['months_covered']} months consistent "
        f"(score {top[0]['stream_score']}/100). "
        f"Diversity bonus applied." if unique_types > 1 else
        f"{len(streams)} bill stream(s). "
        f"Top: {top_name} — {top[0]['months_covered']} months consistent "
        f"(score {top[0]['stream_score']}/100)."
    )
    return final, reason


def _synthetic_fallback(applicant_id: str) -> dict:
    """
    Synthetic baseline used when MongoDB is unavailable or no bills uploaded.
    Returns a neutral-ish score with clear explanation.
    """
    import hashlib, random
    seed = int(hashlib.md5(applicant_id.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    months = rng.randint(4, 12)
    bill_type = rng.choice(["electricity", "phone", "rent_receipt"])
    amount = round(rng.uniform(300, 5000), 0)
    score = _compute_stream_score(bill_type, months, amount, "self_reported")

    streams = [{
        "bill_type": bill_type,
        "payee_name": "Synthetic Utility",
        "months_covered": months,
        "avg_amount": amount,
        "verification_level": "self_reported",
        "stream_score": score,
        "reason": f"Synthetic {bill_type.replace('_',' ')} data — {months} months",
    }]
    final_score, reason = _compute_final_bill_score(streams)
    return {
        "source": "bill_consistency",
        "applicant_id": applicant_id,
        "streams": streams,
        "final_bill_score": final_score,
        "reason": reason + " (synthetic fallback — no real bills uploaded)",
        "bills_uploaded": 0,
        "data_source": "synthetic",
        "status": "synthetic_fallback",
    }


class BillConsistencyScoringTool(CodedTool):
    """
    Reads uploaded bill documents from MongoDB and computes a bill consistency score.

    Called by bill_consistency_agent in the Neuro SAN pipeline.
    Returns per-stream scores + final aggregated score for the agent to narrate.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "bill_consistency",
                "error": "No applicant_id provided",
                "final_bill_score": 45,
                "reason": "Missing applicant ID — using neutral baseline",
                "status": "error",
            }

        try:
            # Import MongoDB helpers (lazy import — avoids issues if Mongo not ready)
            from database_mongo import is_mongo_available, get_mongo_db

            if not is_mongo_available():
                return _synthetic_fallback(applicant_id)

            db = get_mongo_db()

            # Fetch all scored bill documents for this applicant
            cursor = db.bill_documents.find(
                {
                    "applicant_id": applicant_id,
                    "stage": "scored",           # only fully processed bills
                },
                {
                    "file_bytes_b64": 0,         # exclude heavy field
                    "ocr_raw_text": 0,
                }
            )
            docs = []
            async for doc in cursor:
                docs.append(doc)

            if not docs:
                # No bills uploaded yet — synthetic fallback
                return _synthetic_fallback(applicant_id)

            # ── Group into streams: bill_type + payee_name ────────────────
            stream_map: dict[str, dict] = {}
            for doc in docs:
                extraction = doc.get("extraction") or {}
                bill_type  = extraction.get("bill_type", "phone")
                payee      = extraction.get("payee_name", "Unknown")
                key        = f"{bill_type}::{payee}"

                if key not in stream_map:
                    stream_map[key] = {
                        "bill_type":          bill_type,
                        "payee_name":         payee,
                        "amounts":            [],
                        "billing_periods":    set(),
                        "verification_level": doc.get("verification_level", "document_uploaded"),
                        "doc_ids":            [],
                    }

                amt = extraction.get("amount")
                if amt is None:
                    amt = 0
                stream_map[key]["amounts"].append(amt)
                period = extraction.get("billing_period", "")
                if period:
                    stream_map[key]["billing_periods"].add(period)
                stream_map[key]["doc_ids"].append(str(doc["_id"]))

            # ── Compute score per stream ───────────────────────────────────
            streams = []
            for key, s in stream_map.items():
                months_covered = len(s["billing_periods"])
                avg_amount = (
                    sum(s["amounts"]) / len(s["amounts"]) if s["amounts"] else 0
                )
                score = _compute_stream_score(
                    bill_type=s["bill_type"],
                    months_covered=months_covered,
                    avg_amount=avg_amount,
                    verification_level=s["verification_level"],
                )
                bill_label = s["bill_type"].replace("_", " ").title()
                stream_rec = {
                    "bill_type":          s["bill_type"],
                    "payee_name":         s["payee_name"],
                    "months_covered":     months_covered,
                    "avg_amount":         round(avg_amount, 0),
                    "verification_level": s["verification_level"],
                    "stream_score":       score,
                    "reason": (
                        f"{bill_label} payments to {s['payee_name']} — "
                        f"{months_covered} month(s) covered, "
                        f"avg ₹{avg_amount:,.0f}/mo. "
                        f"Verification: {s['verification_level']}."
                    ),
                }
                streams.append(stream_rec)

            final_score, reason = _compute_final_bill_score(streams)

            return {
                "source":           "bill_consistency",
                "applicant_id":     applicant_id,
                "streams":          streams,
                "final_bill_score": final_score,
                "reason":           reason,
                "bills_uploaded":   len(docs),
                "streams_count":    len(streams),
                "data_source":      "mongodb",
                "status":           "success",
            }

        except Exception as e:
            # Never let the tool crash the pipeline
            result = _synthetic_fallback(applicant_id)
            result["tool_error"] = str(e)[:150]
            result["status"] = "error_fallback"
            return result
