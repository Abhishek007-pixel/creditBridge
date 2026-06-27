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
    username: Optional[str] = None
    email: Optional[str] = None   # frontend2 sends email, not username
    password: str

class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: Optional[str] = "applicant"
    phone: Optional[str] = ""
    aadhaar_last4: Optional[str] = "0000"

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
    """Login endpoint. Accepts either email or username field for frontend2 compatibility."""
    identifier = req.email or req.username or ""
    user = authenticate_demo_user(identifier, req.password)
    if not user:
        # Also try stripping domain from email for demo user lookup
        simple_name = identifier.split("@")[0] if "@" in identifier else identifier
        user = authenticate_demo_user(simple_name, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({
        "sub": identifier,
        "role": user["role"],
        "uid": user.get("uid", identifier),
        "name": user.get("name", identifier.split("@")[0]),
        "email": identifier,
    })
    return {
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "user": {
            "uid": user.get("uid", identifier),
            "email": identifier,
            "role": user["role"],
            "name": user.get("name", identifier.split("@")[0]),
        }
    }


@router.post("/auth/register")
def auth_register(req: AuthRegisterRequest):
    """Register a new user via email+password (frontend2 compatibility)."""
    applicant_id = new_id()
    with get_db() as conn:
        # Check if email already registered
        existing = conn.execute(
            "SELECT id FROM applicants WHERE email_encrypted IS NOT NULL LIMIT 1"
        ).fetchall()
        # We do a best-effort search (encryption means we can't do a simple WHERE email=?)
        # For demo purposes, just insert new applicant record
        conn.execute(
            """INSERT INTO applicants
               (id, name, phone_encrypted, email_encrypted, aadhaar_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (
                applicant_id,
                req.name or req.email.split("@")[0],
                encrypt_field(req.phone or ""),
                encrypt_field(req.email),
                hash_aadhaar(req.aadhaar_last4 or "0000"),
            )
        )
        conn.commit()

    token = create_access_token({
        "sub": req.email,
        "role": req.role,
        "uid": applicant_id,
        "name": req.name or req.email.split("@")[0],
        "email": req.email,
    })
    log_audit(applicant_id, "USER_REGISTERED", {"email": req.email, "role": req.role})
    return {
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "role": req.role,
        "user": {
            "uid": applicant_id,
            "email": req.email,
            "role": req.role,
            "name": req.name or req.email.split("@")[0],
        }
    }


@router.get("/auth/me")
def me_old(authorization: Optional[str] = Header(None)):
    """Legacy /api/auth/me endpoint. Kept for backward compatibility."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": payload.get("sub"), "role": payload.get("role")}


@router.get("/me")
def get_me(authorization: Optional[str] = Header(None)):
    """Session restore — returns applicant profile + latest score for the logged-in user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    uid = payload.get("uid")
    if not uid:
        # Fallback: return from token data only
        return {
            "applicant": {
                "id": payload.get("sub"),
                "name": payload.get("name", ""),
                "email": payload.get("email", payload.get("sub", "")),
            },
            "score": None,
        }

    with get_db() as conn:
        applicant = conn.execute(
            "SELECT id, name FROM applicants WHERE id = ?", (uid,)
        ).fetchone()
        score = conn.execute(
            """SELECT final_score, risk_category, loan_recommended,
                      interest_rate, explanation, status
               FROM credit_scores WHERE applicant_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (uid,)
        ).fetchone()

    return {
        "applicant": dict(applicant) if applicant else None,
        "score": dict(score) if score else None,
    }


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
                   cs.loan_recommended, cs.interest_rate, cs.pipeline_mode,
                   cs.status
            FROM applicants a
            LEFT JOIN credit_scores cs ON a.id = cs.applicant_id
            ORDER BY a.created_at DESC
        """).fetchall()

    return {
        "applicants": [
            {
                "id": r["id"],
                "name": r["name"],
                "email": "",       # encrypted — not returned here
                "phone": "",       # encrypted — not returned here
                "aadhaar_last4": "",
                "created_at": r["created_at"],
                "final_score": r["final_score"],
                "risk_category": r["risk_category"],
                "loan_recommended": r["loan_recommended"],
                "interest_rate": r["interest_rate"],
                "pipeline_mode": r["pipeline_mode"],
                "status": r["status"] or "pending",
            }
            for r in rows
        ]
    }


@router.get("/applicants/{applicant_id}/score")
def get_applicant_score(applicant_id: str, authorization: Optional[str] = Header(None)):
    """Get full score breakdown + audit logs for one applicant. Used by BankDashboard detail panel."""
    import json
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

        audit_rows = conn.execute(
            """SELECT action, metadata, timestamp
               FROM audit_log WHERE applicant_id = ?
               ORDER BY timestamp ASC""",
            (applicant_id,)
        ).fetchall()

    score_data = None
    if score_row:
        breakdown = {
            "phone_bill":   {"score": score_row["phone_score"],        "reason": score_row["phone_reason"],        "consented": True, "weight_used": 25},
            "cashflow":     {"score": score_row["cashflow_score"],     "reason": score_row["cashflow_reason"],     "consented": True, "weight_used": 20},
            "geolocation":  {"score": score_row["geo_score"],          "reason": score_row["geo_reason"],          "consented": True, "weight_used": 15},
            "ecommerce":    {"score": score_row["ecommerce_score"],    "reason": score_row["ecommerce_reason"],    "consented": True, "weight_used": 12},
            "merchant":     {"score": score_row["merchant_score"],     "reason": score_row["merchant_reason"],     "consented": True, "weight_used": 8},
            "psychometric": {"score": score_row["psychometric_score"], "reason": score_row["psychometric_reason"], "consented": True, "weight_used": 20},
        }
        # Parse weights_used JSON if available
        try:
            weights_used = json.loads(score_row["weights_used"]) if score_row["weights_used"] else {}
            for key in breakdown:
                agent_key = key.replace("_bill", "").replace("geo", "geolocation") if key == "geolocation" else key
                if key in weights_used:
                    breakdown[key]["weight_used"] = round(weights_used[key] * 100)
        except Exception:
            pass

        score_data = {
            "final_score": score_row["final_score"],
            "risk_category": score_row["risk_category"],
            "loan_recommended": score_row["loan_recommended"],
            "interest_rate": score_row["interest_rate"],
            "explanation": score_row["explanation"],
            "breakdown": breakdown,
            "pipeline_mode": score_row["pipeline_mode"],
            "status": score_row["status"] if "status" in score_row.keys() else "pending",
        }

    logs = []
    for r in audit_rows:
        try:
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
        except Exception:
            meta = r["metadata"]
        logs.append({"action": r["action"], "metadata": meta, "timestamp": r["timestamp"]})

    return {
        "applicant": dict(app_row),
        "score": score_data,
        "logs": logs,
    }

