"""
Scoring routes — triggers the agent pipeline and saves results.
"""
import json
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from database import get_db, new_id, log_audit
from agents.runner import run_agent_pipeline

router = APIRouter(prefix="/api", tags=["scoring"])


class ScoreRequest(BaseModel):
    applicant_id: str
    questionnaire_answers: Optional[list[int]] = []


@router.post("/score")
async def score_applicant(req: ScoreRequest):
    """
    Trigger the full scoring pipeline for an applicant.
    Gets consent status from DB, runs agent pipeline, saves result.
    """
    with get_db() as conn:
        # Check applicant exists
        row = conn.execute(
            "SELECT id, name FROM applicants WHERE id = ?", (req.applicant_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Applicant not found")

        # Get consented sources
        consent_rows = conn.execute(
            """SELECT source_name, consented FROM consent_logs
               WHERE applicant_id = ?
               ORDER BY timestamp DESC""",
            (req.applicant_id,)
        ).fetchall()

    # Get latest consent per source
    seen = {}
    for cr in consent_rows:
        if cr["source_name"] not in seen:
            seen[cr["source_name"]] = bool(cr["consented"])
    consented_sources = [s for s, v in seen.items() if v]

    # Always include psychometric (questionnaire, not a data API)
    if "psychometric" not in consented_sources:
        consented_sources.append("psychometric")

    log_audit(req.applicant_id, "SCORING_STARTED", {
        "consented_sources": consented_sources,
        "answers_count": len(req.questionnaire_answers),
    })

    # Run the pipeline
    result = await run_agent_pipeline(
        applicant_id=req.applicant_id,
        consented_sources=consented_sources,
        questionnaire_answers=req.questionnaire_answers or [],
    )

    # Save to database
    breakdown = result.get("breakdown", {})
    with get_db() as conn:
        # Remove any old score for this applicant (replace)
        conn.execute(
            "DELETE FROM credit_scores WHERE applicant_id = ?",
            (req.applicant_id,)
        )
        conn.execute(
            """INSERT INTO credit_scores
               (id, applicant_id, phone_score, ecommerce_score, geo_score,
                psychometric_score, merchant_score, cashflow_score,
                final_score, risk_category, loan_recommended, interest_rate,
                explanation, phone_reason, ecommerce_reason, geo_reason,
                psychometric_reason, merchant_reason, cashflow_reason,
                weights_used, pipeline_mode)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                new_id(),
                req.applicant_id,
                breakdown.get("phone_bill", {}).get("score", 0),
                breakdown.get("ecommerce", {}).get("score", 0),
                breakdown.get("geolocation", {}).get("score", 0),
                breakdown.get("psychometric", {}).get("score", 0),
                breakdown.get("merchant", {}).get("score", 0),
                breakdown.get("cashflow", {}).get("score", 0),
                result.get("final_score", 0),
                result.get("risk_category", ""),
                result.get("loan_recommended", 0),
                result.get("interest_rate", 0.0),
                result.get("explanation", ""),
                breakdown.get("phone_bill", {}).get("reason", ""),
                breakdown.get("ecommerce", {}).get("reason", ""),
                breakdown.get("geolocation", {}).get("reason", ""),
                breakdown.get("psychometric", {}).get("reason", ""),
                breakdown.get("merchant", {}).get("reason", ""),
                breakdown.get("cashflow", {}).get("reason", ""),
                json.dumps(result.get("weights_used", {})),
                result.get("pipeline_mode", "synthetic"),
            )
        )
        conn.commit()

    log_audit(req.applicant_id, "SCORING_COMPLETED", {
        "final_score": result.get("final_score"),
        "risk_category": result.get("risk_category"),
        "pipeline_mode": result.get("pipeline_mode"),
    })

    return {
        "message": "Scoring complete",
        "applicant_id": req.applicant_id,
        "pipeline_mode": result.get("pipeline_mode"),
        **result,
    }
