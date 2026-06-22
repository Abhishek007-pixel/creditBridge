"""
Applicant registration and consent routes.
"""
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from database import get_db, new_id, log_audit
from auth import encrypt_field, hash_aadhaar, verify_token, create_access_token, authenticate_demo_user

router = APIRouter(prefix="/api", tags=["applicant"])


# ── Request/Response models ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    phone: str
    email: str
    aadhaar_last4: str

class ConsentRequest(BaseModel):
    applicant_id: str
    phone_bill: bool = False
    ecommerce: bool = False
    geolocation: bool = False
    merchant: bool = False
    cashflow: bool = False

class QuestionnaireRequest(BaseModel):
    applicant_id: str
    answers: list[int]


# ── Auth routes ──────────────────────────────────────────────────────────

@router.post("/auth/login")
def login(req: LoginRequest):
    user = authenticate_demo_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": req.username, "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@router.get("/auth/me")
def me(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": payload["sub"], "role": payload["role"]}


# ── Applicant routes ───────────────────────────────────────────────────

@router.post("/register")
def register(req: RegisterRequest):
    """Register a new applicant. Stores encrypted PII, hashed Aadhaar."""
    if len(req.aadhaar_last4) != 4 or not req.aadhaar_last4.isdigit():
        raise HTTPException(status_code=400, detail="aadhaar_last4 must be exactly 4 digits")

    applicant_id = new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO applicants
               (id, name, phone_encrypted, email_encrypted, aadhaar_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (
                applicant_id,
                req.name,
                encrypt_field(req.phone),
                encrypt_field(req.email),
                hash_aadhaar(req.aadhaar_last4),
            )
        )
        conn.commit()

    log_audit(applicant_id, "APPLICANT_REGISTERED", {"name": req.name})
    return {
        "applicant_id": applicant_id,
        "message": "Applicant registered successfully",
        "name": req.name,
    }


@router.post("/consent")
def save_consent(req: ConsentRequest):
    """Save consent decisions. Each source logged individually for audit trail."""
    sources = {
        "phone_bill": req.phone_bill,
        "ecommerce":  req.ecommerce,
        "geolocation": req.geolocation,
        "merchant":   req.merchant,
        "cashflow":   req.cashflow,
    }
    with get_db() as conn:
        # Verify applicant exists
        row = conn.execute(
            "SELECT id FROM applicants WHERE id = ?", (req.applicant_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Applicant not found")

        # Log each consent decision individually (immutable audit trail)
        for source, consented in sources.items():
            conn.execute(
                """INSERT INTO consent_logs (id, applicant_id, source_name, consented)
                   VALUES (?, ?, ?, ?)""",
                (new_id(), req.applicant_id, source, 1 if consented else 0)
            )
        conn.commit()

    consented_list = [s for s, v in sources.items() if v]
    log_audit(req.applicant_id, "CONSENT_RECORDED", {"consented": consented_list})
    return {
        "message": "Consent recorded successfully",
        "consented_sources": consented_list,
        "audit_logged": True,
    }


@router.get("/consent/{applicant_id}")
def get_consent_status(applicant_id: str):
    """Get latest consent status for an applicant."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT source_name, consented, timestamp
               FROM consent_logs WHERE applicant_id = ?
               ORDER BY timestamp DESC""",
            (applicant_id,)
        ).fetchall()

    # Get the latest decision per source
    seen = {}
    for row in rows:
        if row["source_name"] not in seen:
            seen[row["source_name"]] = bool(row["consented"])

    return {
        "applicant_id": applicant_id,
        "consents": seen,
        "consented_sources": [s for s, v in seen.items() if v],
    }


@router.post("/questionnaire")
def save_questionnaire(req: QuestionnaireRequest):
    """Save psychometric questionnaire responses."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM applicants WHERE id = ?", (req.applicant_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Applicant not found")

        conn.execute(
            """INSERT INTO questionnaire_responses (id, applicant_id, answers)
               VALUES (?, ?, ?)""",
            (new_id(), req.applicant_id, json.dumps(req.answers))
        )
        conn.commit()

    log_audit(req.applicant_id, "QUESTIONNAIRE_SUBMITTED", {"num_answers": len(req.answers)})
    return {
        "message": "Questionnaire submitted successfully",
        "answers_count": len(req.answers),
    }


@router.get("/applicants")
def list_applicants(authorization: Optional[str] = Header(None)):
    """List all applicants with their latest scores. For bank officer dashboard."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.id, a.name, a.created_at,
                   cs.final_score, cs.risk_category,
                   cs.loan_recommended, cs.interest_rate, cs.pipeline_mode
            FROM applicants a
            LEFT JOIN credit_scores cs ON a.id = cs.applicant_id
            ORDER BY a.created_at DESC
        """).fetchall()

    return {
        "applicants": [
            {
                "id": r["id"],
                "name": r["name"],
                "created_at": r["created_at"],
                "final_score": r["final_score"],
                "risk_category": r["risk_category"],
                "loan_recommended": r["loan_recommended"],
                "interest_rate": r["interest_rate"],
                "pipeline_mode": r["pipeline_mode"],
            }
            for r in rows
        ]
    }
