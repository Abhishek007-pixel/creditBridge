"""
MerchantScoringTool — Neuro SAN CodedTool
"""
from typing import Any, Union
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_merchant


class MerchantScoringTool(CodedTool):

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
            merch_data = data["merchant"]
            score, reason = score_merchant(merch_data)
            return {
                "source": "merchant",
                "applicant_id": applicant_id,
                "data": merch_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {"source": "merchant", "error": str(e), "score": 50, "status": "error"}
