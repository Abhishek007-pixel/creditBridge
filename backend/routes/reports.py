"""
Report retrieval routes.
"""
import json
from fastapi import APIRouter, HTTPException
from database import get_db, log_audit

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/report/{applicant_id}")
def get_report(applicant_id: str):
    """Get the full credit report for an applicant."""
    with get_db() as conn:
        app_row = conn.execute(
            "SELECT id, name, created_at FROM applicants WHERE id = ?",
            (applicant_id,)
        ).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="Applicant not found")

        score_row = conn.execute(
            """SELECT * FROM credit_scores WHERE applicant_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (applicant_id,)
        ).fetchone()

        consent_rows = conn.execute(
            """SELECT source_name, consented FROM consent_logs
               WHERE applicant_id = ?
               ORDER BY timestamp DESC""",
            (applicant_id,)
        ).fetchall()

    # Build consent map
    consent_map = {}
    for cr in consent_rows:
        if cr["source_name"] not in consent_map:
            consent_map[cr["source_name"]] = bool(cr["consented"])

    if not score_row:
        return {
            "applicant_id": applicant_id,
            "name": app_row["name"],
            "scored": False,
            "consents": consent_map,
        }

    breakdown = {
        "phone_bill":   {"score": score_row["phone_score"],        "reason": score_row["phone_reason"]},
        "ecommerce":    {"score": score_row["ecommerce_score"],    "reason": score_row["ecommerce_reason"]},
        "geolocation":  {"score": score_row["geo_score"],          "reason": score_row["geo_reason"]},
        "psychometric": {"score": score_row["psychometric_score"], "reason": score_row["psychometric_reason"]},
        "merchant":     {"score": score_row["merchant_score"],     "reason": score_row["merchant_reason"]},
        "cashflow":     {"score": score_row["cashflow_score"],     "reason": score_row["cashflow_reason"]},
    }

    return {
        "applicant_id":    applicant_id,
        "name":            app_row["name"],
        "scored":          True,
        "final_score":     score_row["final_score"],
        "risk_category":   score_row["risk_category"],
        "loan_recommended": score_row["loan_recommended"],
        "interest_rate":   score_row["interest_rate"],
        "explanation":     score_row["explanation"],
        "breakdown":       breakdown,
        "consents":        consent_map,
        "pipeline_mode":   score_row["pipeline_mode"],
        "scored_at":       score_row["created_at"],
    }


@router.get("/audit/{applicant_id}")
def get_audit_log(applicant_id: str):
    """Get the audit trail for an applicant. Shows all system actions."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT action, metadata, timestamp
               FROM audit_log WHERE applicant_id = ?
               ORDER BY timestamp ASC""",
            (applicant_id,)
        ).fetchall()
    return {
        "applicant_id": applicant_id,
        "audit_trail": [
            {
                "action": r["action"],
                "metadata": json.loads(r["metadata"]),
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]
    }
