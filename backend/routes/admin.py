"""
Admin panel routes — weight configuration, analytics, and status management.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from database import get_db, log_audit
from auth import verify_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


class WeightUpdateRequest(BaseModel):
    weights: dict[str, float]


class StatusUpdateRequest(BaseModel):
    status: str          # "approved" or "rejected"
    decided_by: Optional[str] = None


def require_admin(authorization: Optional[str] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(authorization.split(" ")[1])
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


@router.get("/weights")
def get_weights(authorization: Optional[str] = Header(None)):
    """Get current agent weights."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT agent_name, weight, updated_at FROM agent_weights"
        ).fetchall()
    return {
        "weights": {r["agent_name"]: r["weight"] for r in rows},
        "updated_at": {r["agent_name"]: r["updated_at"] for r in rows},
    }


@router.put("/weights")
def update_weights(
    req: WeightUpdateRequest,
    authorization: Optional[str] = Header(None)
):
    """Update agent weights. Admin only. Weights must sum to ~1.0."""
    require_admin(authorization)
    total = sum(req.weights.values())
    if not (0.95 <= total <= 1.05):
        raise HTTPException(
            status_code=400,
            detail=f"Weights must sum to 1.0. Current sum: {total:.3f}"
        )
    with get_db() as conn:
        for agent, weight in req.weights.items():
            conn.execute(
                """INSERT INTO agent_weights (agent_name, weight, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(agent_name) DO UPDATE SET
                   weight=excluded.weight, updated_at=excluded.updated_at""",
                (agent, weight)
            )
        conn.commit()
    log_audit(None, "WEIGHTS_UPDATED", {"new_weights": req.weights})
    return {"message": "Weights updated", "weights": req.weights}


@router.get("/analytics")
def get_analytics(authorization: Optional[str] = Header(None)):
    """Dashboard statistics for the admin panel."""
    with get_db() as conn:
        total_apps = conn.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]
        total_scored = conn.execute(
            "SELECT COUNT(*) FROM credit_scores"
        ).fetchone()[0]
        avg_score = conn.execute(
            "SELECT AVG(final_score) FROM credit_scores"
        ).fetchone()[0]
        risk_dist = conn.execute(
            """SELECT risk_category, COUNT(*) as count
               FROM credit_scores GROUP BY risk_category"""
        ).fetchall()
        pipeline_dist = conn.execute(
            """SELECT pipeline_mode, COUNT(*) as count
               FROM credit_scores GROUP BY pipeline_mode"""
        ).fetchall()

    return {
        "total_applicants": total_apps,
        "total_scored": total_scored,
        "average_score": round(avg_score, 1) if avg_score else 0,
        "risk_distribution": {r["risk_category"]: r["count"] for r in risk_dist},
        "pipeline_distribution": {r["pipeline_mode"]: r["count"] for r in pipeline_dist},
    }


@router.post("/applicants/{applicant_id}/status")
def update_applicant_status(
    applicant_id: str,
    req: StatusUpdateRequest,
    authorization: Optional[str] = Header(None)
):
    """Bank officer approves or rejects a scored applicant."""
    if req.status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="status must be 'approved', 'rejected', or 'pending'")
    with get_db() as conn:
        # Try updating with status column; if column doesn't exist, skip gracefully
        try:
            conn.execute(
                "UPDATE credit_scores SET status = ? WHERE applicant_id = ?",
                (req.status, applicant_id)
            )
            conn.commit()
        except Exception as e:
            # Column may not exist yet in existing DB — ALTER TABLE to add it
            try:
                conn.execute("ALTER TABLE credit_scores ADD COLUMN status TEXT DEFAULT 'pending'")
                conn.execute(
                    "UPDATE credit_scores SET status = ? WHERE applicant_id = ?",
                    (req.status, applicant_id)
                )
                conn.commit()
            except Exception:
                pass
    log_audit(applicant_id, f"STATUS_{req.status.upper()}", {"decided_by": req.decided_by})
    return {"success": True, "status": req.status}


@router.get("/audit")
def get_all_audit_logs(authorization: Optional[str] = Header(None)):
    """Get global audit trail for admin panel. Returns all system events."""
    import json
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, applicant_id, action, metadata, timestamp
               FROM audit_log ORDER BY timestamp DESC LIMIT 500"""
        ).fetchall()
    logs = []
    for r in rows:
        try:
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
        except Exception:
            meta = r["metadata"]
        logs.append({
            "id": r["id"],
            "applicant_id": r["applicant_id"],
            "action": r["action"],
            "metadata": meta,
            "timestamp": r["timestamp"],
        })
    return {"logs": logs}
