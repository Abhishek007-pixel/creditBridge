"""
GeolocationScoringTool — Neuro SAN CodedTool
"""
from typing import Any, Union
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_geolocation


class GeolocationScoringTool(CodedTool):

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
            geo_data = data["geolocation"]
            score, reason = score_geolocation(geo_data)
            return {
                "source": "geolocation",
                "applicant_id": applicant_id,
                "data": geo_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {"source": "geolocation", "error": str(e), "score": 50, "status": "error"}
