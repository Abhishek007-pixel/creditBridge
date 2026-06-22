"""
CashflowScoringTool — Neuro SAN CodedTool
"""
from typing import Any, Union
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_cashflow


class CashflowScoringTool(CodedTool):

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any]
    ) -> Union[dict[str, Any], str]:
        applicant_id = args.get("applicant_id", "")
        if not applicant_id:
            return {"error": "No applicant_id provided", "score": 50}

        try:
            data = generate_applicant_data(applicant_id)
            cf_data = data["cashflow"]
            score, reason = score_cashflow(cf_data)
            return {
                "source": "cashflow",
                "applicant_id": applicant_id,
                "data": cf_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {"source": "cashflow", "error": str(e), "score": 50, "status": "error"}
