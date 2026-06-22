"""
PhoneBillScoringTool — Neuro SAN CodedTool
Fetches and returns phone bill data for the scoring agent.
"""
from typing import Any, Union
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_phone_bill


class PhoneBillScoringTool(CodedTool):
    """
    Neuro SAN CodedTool: fetches phone bill data for an applicant
    and returns structured data for the phone_bill_agent to score.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any]
    ) -> Union[dict[str, Any], str]:
        applicant_id = args.get("applicant_id", "")
        if not applicant_id:
            return {"error": "No applicant_id provided", "score": 50, "reason": "Missing ID"}

        try:
            data = generate_applicant_data(applicant_id)
            phone_data = data["phone_bill"]
            score, reason = score_phone_bill(phone_data)

            return {
                "source": "phone_bill",
                "applicant_id": applicant_id,
                "data": phone_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {
                "source": "phone_bill",
                "error": str(e),
                "score": 50,
                "reason": "Data fetch failed — using neutral score",
                "status": "error"
            }
