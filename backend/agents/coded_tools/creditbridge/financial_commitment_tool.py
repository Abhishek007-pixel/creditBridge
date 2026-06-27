"""
FinancialCommitmentScoringTool — Neuro SAN CodedTool
Reads long-term savings commitment records from MongoDB financial_commitments,
scores consistency (months active), average commitment amount, and plan diversity,
and falls back to synthetic generator if MongoDB is empty.
"""
import os
import sys
import logging
from datetime import datetime
from typing import Any, Union

_this_dir = os.path.dirname(os.path.abspath(__file__))
for _levels_up in (3, 4):
    _candidate = os.path.abspath(os.path.join(_this_dir, *(['..'] * _levels_up)))
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_financial_commitment

logger = logging.getLogger(__name__)


def _synthetic_fallback(applicant_id: str) -> dict:
    try:
        data = generate_applicant_data(applicant_id)
        commitment_data = data["financial_commitment"]
        score, reason = score_financial_commitment(commitment_data)
        return {
            "source": "financial_commitment",
            "applicant_id": applicant_id,
            "score": score,
            "preliminary_score": score,
            "reason": reason + " (synthetic fallback — no real commitments uploaded)",
            "preliminary_reason": reason + " (synthetic fallback — no real commitments uploaded)",
            "raw_data": commitment_data,
            "data_source": "synthetic",
            "status": "synthetic_fallback"
        }
    except Exception as e:
        return {
            "source": "financial_commitment",
            "applicant_id": applicant_id,
            "score": 40,
            "preliminary_score": 40,
            "reason": f"Fallback error: {str(e)[:80]}",
            "preliminary_reason": f"Fallback error: {str(e)[:80]}",
            "data_source": "error",
            "status": "error"
        }


class FinancialCommitmentScoringTool(CodedTool):
    """
    Evaluates applicant's long-term savings behaviors and premium payments consistency.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "financial_commitment",
                "error": "No applicant_id provided",
                "score": 40,
                "preliminary_score": 40,
                "reason": "Missing applicant ID",
                "preliminary_reason": "Missing applicant ID",
                "status": "error",
            }

        try:
            from database_mongo import is_mongo_available, get_mongo_db
            
            if not is_mongo_available():
                return _synthetic_fallback(applicant_id)

            db = get_mongo_db()
            
            # Fetch all scored commitments
            cursor = db.financial_commitments.find({
                "applicant_id": applicant_id,
                "stage": "scored"
            })
            commitments = []
            async for doc in cursor:
                commitments.append(doc)

            if not commitments:
                return _synthetic_fallback(applicant_id)

            # Perform calculations
            count = len(commitments)
            
            # Extract distinct months
            months = set()
            types = set()
            amounts = []
            for c in commitments:
                p_date = c.get("payment_date")
                if p_date and len(p_date) >= 7:
                    months.add(p_date[:7])  # YYYY-MM
                p_type = c.get("policy_type")
                if p_type:
                    types.add(p_type)
                amounts.append(float(c.get("amount") or 0.0))

            # 1. Consistency Score (8 points per unique month, up to 50 max)
            unique_months = len(months)
            consistency_score = min(50, unique_months * 8)
            
            # 2. Average amount commitment score
            avg_amount = sum(amounts) / len(amounts) if amounts else 0
            if avg_amount >= 5000:
                amount_score = 25
            elif avg_amount >= 2000:
                amount_score = 15
            elif avg_amount >= 500:
                amount_score = 10
            else:
                amount_score = 5
                
            # 3. Plan Diversity Score
            unique_types = len(types)
            if unique_types >= 2:
                diversity_score = 25
            elif unique_types == 1:
                diversity_score = 10
            else:
                diversity_score = 0
                
            final_score = min(100, consistency_score + amount_score + diversity_score)
            
            # Formatting categories list
            categories_str = ", ".join(types) if types else "unknown types"
            reason = (
                f"Parsed {count} saving/premium record(s) across {unique_types} plan type(s) ({categories_str}). "
                f"Consistency: {unique_months} month(s) verified. Avg premium: ₹{avg_amount:,.0f}."
            )

            return {
                "source": "financial_commitment",
                "applicant_id": applicant_id,
                "score": final_score,
                "preliminary_score": final_score,
                "reason": reason,
                "preliminary_reason": reason,
                "metrics": {
                    "document_count": count,
                    "avg_amount": round(avg_amount, 0),
                    "unique_months": unique_months,
                    "diversity_types": list(types),
                },
                "raw_data": {
                    "has_savings": True,
                    "commitments": [
                        {
                            "provider": c.get("provider", "Unknown"),
                            "amount": float(c.get("amount") or 0.0),
                            "policy_type": c.get("policy_type", "insurance"),
                            "months_active": unique_months
                        } for c in commitments
                    ]
                },
                "data_source": "mongodb",
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Financial commitment tool error: {e}")
            fallback = _synthetic_fallback(applicant_id)
            fallback["tool_error"] = str(e)[:150]
            fallback["status"] = "error_fallback"
            return fallback
