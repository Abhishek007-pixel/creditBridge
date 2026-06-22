"""
CashflowScoringTool — Neuro SAN CodedTool
Fetches bank cashflow data and returns it to the cashflow_agent for scoring.
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
from data.synthetic_generator import generate_applicant_data, score_cashflow


class CashflowScoringTool(CodedTool):
    """
    Fetches bank cashflow pattern data for an applicant.
    Returns structured data for the cashflow_agent to score.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "cashflow",
                "error": "No applicant_id provided",
                "score": 50,
                "reason": "Missing ID — using neutral baseline",
                "status": "error",
            }

        try:
            data = generate_applicant_data(applicant_id)
            cashflow_data = data["cashflow"]
            score, reason = score_cashflow(cashflow_data)

            return {
                "source": "cashflow",
                "applicant_id": applicant_id,
                "raw_data": cashflow_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success",
            }
        except Exception as e:
            return {
                "source": "cashflow",
                "error": str(e),
                "score": 50,
                "reason": f"Tool error: {str(e)[:80]}",
                "status": "error",
            }
