"""
EcommerceScoringTool — Neuro SAN CodedTool
Fetches e-commerce behavior data and returns it to the ecommerce_agent for scoring.
"""
import os
import sys
from typing import Any, Union

_this_dir = os.path.dirname(os.path.abspath(__file__))
for _levels_up in (3, 4):
    _candidate = os.path.abspath(os.path.join(_this_dir, *(['..'] * _levels_up)))
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_ecommerce


class EcommerceScoringTool(CodedTool):
    """
    Fetches e-commerce purchase behavior data for an applicant.
    Returns structured data for the ecommerce_agent to score.
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
                "score": 50,
                "reason": "Missing ID — using neutral baseline",
                "status": "error",
            }

        try:
            data = generate_applicant_data(applicant_id)
            ecommerce_data = data["ecommerce"]
            score, reason = score_ecommerce(ecommerce_data)

            return {
                "source": "ecommerce",
                "applicant_id": applicant_id,
                "raw_data": ecommerce_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success",
            }
        except Exception as e:
            return {
                "source": "ecommerce",
                "error": str(e),
                "score": 50,
                "reason": f"Tool error: {str(e)[:80]}",
                "status": "error",
            }
