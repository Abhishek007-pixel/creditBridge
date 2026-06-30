"""
EcommerceScoringTool — Neuro SAN CodedTool
Reads real purchase invoices from MongoDB ecommerce_invoices,
calculates base score (frequency, prepaid percentage, stability),
applies +15 points Livelihood Asset Bonus if applicable,
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
from data.synthetic_generator import generate_applicant_data, score_ecommerce

logger = logging.getLogger(__name__)


def _synthetic_fallback(applicant_id: str) -> dict:
    try:
        data = generate_applicant_data(applicant_id)
        ecommerce_data = data["ecommerce"]
        score, reason = score_ecommerce(ecommerce_data)
        return {
            "source": "ecommerce",
            "applicant_id": applicant_id,
            "score": score,
            "preliminary_score": score,
            "reason": reason + " (synthetic fallback — no real invoices uploaded)",
            "preliminary_reason": reason + " (synthetic fallback — no real invoices uploaded)",
            "raw_data": ecommerce_data,
            "data_source": "synthetic",
            "status": "synthetic_fallback"
        }
    except Exception as e:
        return {
            "source": "ecommerce",
            "applicant_id": applicant_id,
            "score": 40,
            "preliminary_score": 40,
            "reason": f"Fallback error: {str(e)[:80]}",
            "preliminary_reason": f"Fallback error: {str(e)[:80]}",
            "data_source": "error",
            "status": "error"
        }


class EcommerceScoringTool(CodedTool):
    """
    Evaluates e-commerce purchase history and rewards livelihood investments.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "ecommerce",
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
            
            # Fetch all scored e-commerce invoices
            cursor = db.ecommerce_invoices.find({
                "applicant_id": applicant_id,
                "stage": "scored"
            })
            invoices = []
            async for doc in cursor:
                invoices.append(doc)

            if not invoices:
                return _synthetic_fallback(applicant_id)

            # Perform calculations
            count = len(invoices)
            
            # 1. Frequency (5 pts per invoice, up to 40 max)
            freq_score = min(40, count * 5)
            
            # 2. Prepaid ratio (Prepaid vs COD vs Mixed)
            prepaid_count = sum(1 for inv in invoices if inv.get("payment_method") == "Prepaid")
            mixed_count = sum(1 for inv in invoices if inv.get("payment_method") == "Mixed")
            prepaid_ratio = prepaid_count / count if count > 0 else 0
            mixed_ratio = mixed_count / count if count > 0 else 0
            
            if prepaid_ratio >= 0.75:
                pay_score = 30
            elif (prepaid_ratio + mixed_ratio) >= 0.5:
                pay_score = 15
            else:
                pay_score = 5
                
            # 3. Average order value (₹500 - ₹5000 is ideal)
            amounts = [float(inv.get("amount") or 0.0) for inv in invoices]
            avg_amount = sum(amounts) / len(amounts) if amounts else 0
            if 500 <= avg_amount <= 5000:
                amount_score = 15
            else:
                amount_score = 5
                
            # 4. History stability (time difference earliest to latest)
            dates = []
            for inv in invoices:
                d_str = inv.get("date")
                if d_str:
                    try:
                        dates.append(datetime.strptime(d_str, "%Y-%m-%d"))
                    except ValueError:
                        pass
                        
            if len(dates) >= 2:
                earliest = min(dates)
                latest = max(dates)
                delta_days = (latest - earliest).days
                if delta_days >= 180:  # > 6 months
                    history_score = 15
                elif delta_days >= 90:  # > 3 months
                    history_score = 10
                else:
                    history_score = 5
            else:
                history_score = 5

            # Sum base score
            base_score = freq_score + pay_score + amount_score + history_score
            base_score = min(100, max(0, base_score))
            
            # 5. Livelihood asset bonus (+15 pts if any invoice has is_livelihood_asset: true)
            has_livelihood = any(inv.get("is_livelihood_asset") is True for inv in invoices)
            bonus = 15 if has_livelihood else 0
            final_score = min(100, base_score + bonus)
            
            reason = (
                f"{count} invoice(s) analyzed. Avg spent: ₹{avg_amount:,.0f}. "
                f"Prepaid ratio: {round(prepaid_ratio*100)}%. "
            )
            if has_livelihood:
                reason += "Livelihood asset bonus of +15 points applied (income-generating investments detected)."
            else:
                reason += "No livelihood assets detected in purchases."

            return {
                "source": "ecommerce",
                "applicant_id": applicant_id,
                "score": final_score,
                "preliminary_score": final_score,
                "reason": reason,
                "preliminary_reason": reason,
                "metrics": {
                    "invoice_count": count,
                    "avg_amount": round(avg_amount, 0),
                    "prepaid_percentage": round(prepaid_ratio * 100, 1),
                    "has_livelihood_asset": has_livelihood,
                },
                "raw_data": {
                    "platform": invoices[0].get("platform", "Unknown"),
                    "total_orders": count,
                    "avg_order_value": avg_amount,
                    "payment_method": "Prepaid" if prepaid_ratio >= 0.75 else "Mixed" if (prepaid_ratio+mixed_ratio)>=0.5 else "COD",
                    "account_age_months": round(delta_days/30.0) if len(dates)>=2 else 1,
                    "has_livelihood_asset": has_livelihood,
                },
                "data_source": "mongodb",
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Ecommerce tool error: {e}")
            fallback = _synthetic_fallback(applicant_id)
            fallback["tool_error"] = str(e)[:150]
            fallback["status"] = "error_fallback"
            return fallback
