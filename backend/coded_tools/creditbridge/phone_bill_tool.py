"""
PhoneBillScoringTool — Neuro SAN CodedTool
Fetches phone bill data and returns it to the phone_bill_agent for scoring.

Neuro SAN CodedTool reference:
https://github.com/cognizant-ai-lab/neuro-san/blob/main/neuro_san/interfaces/coded_tool.py
"""
import os
import sys
from typing import Any, Union

# Add backend root to path so data.synthetic_generator can be imported.
# Works from both coded_tools/creditbridge/ and agents/coded_tools/creditbridge/
_this_dir = os.path.dirname(os.path.abspath(__file__))
for _levels_up in (3, 4):
    _candidate = os.path.abspath(os.path.join(_this_dir, *(['..'] * _levels_up)))
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_phone_bill


class PhoneBillScoringTool(CodedTool):
    """
    Fetches phone bill payment history for an applicant.
    Returns structured data for the phone_bill_agent to score.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "phone_bill",
                "error": "No applicant_id provided",
                "score": 50,
                "reason": "Missing ID — using neutral baseline",
                "status": "error",
            }

        try:
            data = generate_applicant_data(applicant_id)
            phone_data = data["phone_bill"]
            score, reason = score_phone_bill(phone_data)

            return {
                "source": "phone_bill",
                "applicant_id": applicant_id,
                "raw_data": phone_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success",
            }
        except Exception as e:
            return {
                "source": "phone_bill",
                "error": str(e),
                "score": 50,
                "reason": f"Tool error: {str(e)[:80]}",
                "status": "error",
            }
