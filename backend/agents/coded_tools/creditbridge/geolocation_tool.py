"""
GeolocationScoringTool — Neuro SAN CodedTool
Redesigned to support:
1. Aadhaar address OCR parsing verification.
2. Device GPS proximity comparison.
3. Bank billing address alignment.
Falls back to synthetic generator if MongoDB is empty.
"""
import os
import sys
import logging
import math
from datetime import datetime
from typing import Any, Union

_this_dir = os.path.dirname(os.path.abspath(__file__))
for _levels_up in (3, 4):
    _candidate = os.path.abspath(os.path.join(_this_dir, *(['..'] * _levels_up)))
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_geolocation

logger = logging.getLogger(__name__)

# Dictionary of major Indian pin code coordinates for local geodetic lookups
PIN_COORDINATES = {
    "110001": (28.6139, 77.2090),  # Delhi
    "400001": (18.9750, 72.8258),  # Mumbai
    "560001": (12.9716, 77.5946),  # Bangalore
    "781001": (26.1445, 91.7362),  # Guwahati
}


def haversine_distance(coord1: tuple, coord2: tuple) -> float:
    """Calculate distance in kilometers between two lat/lon coordinates."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _synthetic_fallback(applicant_id: str) -> dict:
    try:
        data = generate_applicant_data(applicant_id)
        geo_data = data["geolocation"]
        score, reason = score_geolocation(geo_data)
        return {
            "source": "geolocation",
            "applicant_id": applicant_id,
            "score": score,
            "preliminary_score": score,
            "reason": reason + " (synthetic fallback — no real location data)",
            "preliminary_reason": reason + " (synthetic fallback — no real location data)",
            "raw_data": geo_data,
            "data_source": "synthetic",
            "status": "success"
        }
    except Exception as e:
        return {
            "source": "geolocation",
            "applicant_id": applicant_id,
            "score": 40,
            "preliminary_score": 40,
            "reason": f"Fallback error: {str(e)[:80]}",
            "preliminary_reason": f"Fallback error: {str(e)[:80]}",
            "data_source": "error",
            "status": "error"
        }


class GeolocationScoringTool(CodedTool):
    """
    Combines Live GPS, parsed Aadhaar, and Bank Address to score location stability and alignment.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any],
    ) -> Union[dict[str, Any], str]:

        applicant_id = args.get("applicant_id", "").strip()
        if not applicant_id:
            return {
                "source": "geolocation",
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

            # Load Aadhaar address
            aadhaar_doc = await db.aadhaar_addresses.find_one({
                "applicant_id": applicant_id,
                "stage": "scored"
            })

            # Load Live GPS capture
            gps_doc = await db.gps_verifications.find_one({"applicant_id": applicant_id})

            # Load Bank Statement / Account Aggregator billing profile details
            aa_doc = await db.account_aggregators.find_one({"applicant_id": applicant_id})

            if not aadhaar_doc and not gps_doc:
                return _synthetic_fallback(applicant_id)

            # ── 1. Document Alignment (40 Points Max) ──────────────────────────
            aadhaar_pin = str(aadhaar_doc.get("pin_code") or "").strip() if aadhaar_doc else ""
            aadhaar_city = str(aadhaar_doc.get("city") or "").strip().lower() if aadhaar_doc else ""
            aadhaar_state = str(aadhaar_doc.get("state") or "").strip().lower() if aadhaar_doc else ""

            # Check bank/AA profile address (Billing Address)
            bank_pin = ""
            bank_city = ""
            bank_state = ""
            if aa_doc and isinstance(aa_doc, dict):
                profile = aa_doc.get("profile", {})
                if isinstance(profile, dict):
                    addr = profile.get("address", {})
                    if isinstance(addr, dict):
                        bank_pin = str(addr.get("pin_code") or "").strip()
                        bank_city = str(addr.get("city") or "").strip().lower()
                        bank_state = str(addr.get("state") or "").strip().lower()

            if not bank_pin and aa_doc:
                bank_pin = str(aa_doc.get("billing_pin_code") or "").strip()
                bank_city = str(aa_doc.get("billing_city") or "").strip().lower()
                bank_state = str(aa_doc.get("billing_state") or "").strip().lower()

            # Default scoring baseline if one document is missing
            if not aadhaar_pin or not bank_pin:
                doc_score = 25  # Mid-score for single verified document
            elif aadhaar_pin == bank_pin:
                doc_score = 40
            elif aadhaar_city == bank_city and aadhaar_city:
                doc_score = 30
            elif aadhaar_state == bank_state and aadhaar_state:
                doc_score = 15
            else:
                doc_score = 5

            # ── 2. Physical Presence Proximity (40 Points Max) ──────────────────
            gps_lat = gps_doc.get("latitude") if gps_doc else None
            gps_lon = gps_doc.get("longitude") if gps_doc else None
            
            proximity_score = 10  # Baseline if GPS is missing or mismatch
            min_dist = float('inf')
            
            if gps_lat is not None and gps_lon is not None:
                gps_coord = (gps_lat, gps_lon)
                
                # Check distances to document locations
                comparison_points = []
                if aadhaar_pin in PIN_COORDINATES:
                    comparison_points.append(PIN_COORDINATES[aadhaar_pin])
                if bank_pin in PIN_COORDINATES:
                    comparison_points.append(PIN_COORDINATES[bank_pin])
                    
                for pt in comparison_points:
                    dist = haversine_distance(gps_coord, pt)
                    if dist < min_dist:
                        min_dist = dist
                        
                if min_dist <= 15.0:
                    proximity_score = 40
                elif min_dist <= 50.0:
                    proximity_score = 25
                else:
                    proximity_score = 10
            else:
                # No live GPS verify, baseline
                proximity_score = 25

            # ── 3. Address History Stability (20 Points Max) ────────────────────
            # Assume stable history if both documents match, or bank account has history
            stability_score = 10
            if doc_score >= 30:
                stability_score = 20
            elif aa_doc:
                # If AA linked, implies established account age stability
                stability_score = 15

            final_score = min(100, max(0, doc_score + proximity_score + stability_score))
            
            aadhaar_city_str = aadhaar_doc.get("city") if aadhaar_doc else "Unknown"
            bank_city_str = bank_city.capitalize() if bank_city else "Unknown"
            gps_city_str = gps_doc.get("city") if gps_doc else "Unknown"
            
            reason = (
                f"Aadhaar registered city: {aadhaar_city_str}. Bank statement city: {bank_city_str}. "
                f"Live location: {gps_city_str}. "
            )
            if min_dist != float('inf'):
                reason += f"Device matches verified permanent coordinates within {round(min_dist, 1)} km."
            else:
                reason += "No live GPS coordinates cross-referenced."

            return {
                "source": "geolocation",
                "applicant_id": applicant_id,
                "score": final_score,
                "preliminary_score": final_score,
                "reason": reason,
                "preliminary_reason": reason,
                "metrics": {
                    "document_alignment_score": doc_score,
                    "presence_proximity_score": proximity_score,
                    "stability_score": stability_score,
                    "haversine_distance_km": round(min_dist, 1) if min_dist != float('inf') else None,
                    "aadhaar_city": aadhaar_city_str,
                    "bank_city": bank_city_str,
                    "gps_city": gps_city_str
                },
                "data_source": "mongodb",
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Geolocation tool error: {e}")
            fallback = _synthetic_fallback(applicant_id)
            fallback["tool_error"] = str(e)[:150]
            return fallback
