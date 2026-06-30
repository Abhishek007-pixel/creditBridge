"""
Applicant registration and consent routes.
"""
import json
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

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
    uid: Optional[str] = None

class ConsentRequest(BaseModel):
    applicant_id: str
    phone_bill: bool = False
    ecommerce: bool = False
    geolocation: bool = False
    merchant: bool = False
    cashflow: bool = False
    financial_commitment: bool = False

class QuestionnaireRequest(BaseModel):
    applicant_id: str
    answers: list[int]


# ── Auth routes ──────────────────────────────────────────────────────────

@router.post("/auth/login")
async def login(req: LoginRequest):
    """Login endpoint. Accepts either email or username field, checks MongoDB Atlas, and falls back to demo credentials."""
    identifier = req.email or req.username or ""
    
    from database_mongo import is_mongo_available, get_user_from_mongo, create_user_in_mongo
    from auth import hash_password, verify_password
    
    user = None
    if is_mongo_available():
        try:
            mongo_user = await get_user_from_mongo(identifier)
            if mongo_user:
                if verify_password(req.password, mongo_user.get("password_hash", "")):
                    user = {
                        "uid": mongo_user["uid"],
                        "email": mongo_user["email"],
                        "role": mongo_user["role"],
                        "name": mongo_user.get("name", mongo_user["email"].split("@")[0])
                    }
                else:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"MongoDB login query failed, falling back to demo users: {e}")

    if not user:
        # Fall back to hardcoded demo users
        demo_user = authenticate_demo_user(identifier, req.password)
        if not demo_user:
            simple_name = identifier.split("@")[0] if "@" in identifier else identifier
            demo_user = authenticate_demo_user(simple_name, req.password)
        
        if demo_user:
            uid = demo_user.get("uid", identifier)
            role = demo_user["role"]
            name = demo_user.get("name", identifier.split("@")[0])
            user = {
                "uid": uid,
                "email": identifier,
                "role": role,
                "name": name
            }
            # Seed the demo user to MongoDB so it's stored there
            if is_mongo_available():
                try:
                    await create_user_in_mongo({
                        "uid": uid,
                        "email": identifier,
                        "name": name,
                        "role": role,
                        "password_hash": hash_password(req.password)
                    })
                except Exception as e:
                    logger.warning(f"Failed to seed demo user to MongoDB: {e}")
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": user["email"],
        "role": user["role"],
        "uid": user["uid"],
        "name": user["name"],
        "email": user["email"],
    })
    return {
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "user": {
            "uid": user["uid"],
            "email": user["email"],
            "role": user["role"],
            "name": user["name"],
        }
    }


@router.post("/auth/register")
async def auth_register(req: AuthRegisterRequest):
    """Register a new user via email+password (frontend2 compatibility)."""
    applicant_id = new_id()
    from auth import hash_password
    with get_db() as conn:
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

    # Write to MongoDB Atlas users collection
    from database_mongo import is_mongo_available, create_user_in_mongo
    if is_mongo_available():
        try:
            await create_user_in_mongo({
                "uid": applicant_id,
                "email": req.email,
                "name": req.name or req.email.split("@")[0],
                "role": req.role or "applicant",
                "phone": req.phone or "",
                "aadhaar_last4": req.aadhaar_last4 or "0000",
                "password_hash": hash_password(req.password),
            })
        except Exception as e:
            logger.warning(f"Failed to register user in MongoDB: {e}")

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
        score_row = conn.execute(
            """SELECT * FROM credit_scores WHERE applicant_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (uid,)
        ).fetchone()
        consent_rows = conn.execute(
            """SELECT source_name, consented FROM consent_logs
               WHERE applicant_id = ?
               ORDER BY timestamp DESC""",
            (uid,)
        ).fetchall()

    consent_map = {}
    for cr in consent_rows:
        if cr["source_name"] not in consent_map:
            consent_map[cr["source_name"]] = bool(cr["consented"])

    score_data = None
    if score_row:
        breakdown = {
            "phone_bill":   {"score": score_row["phone_score"],        "reason": score_row["phone_reason"],        "consented": consent_map.get("phone_bill", consent_map.get("bill_consistency", True)), "weight_used": 20},
            "cashflow":     {"score": score_row["cashflow_score"],     "reason": score_row["cashflow_reason"],     "consented": consent_map.get("cashflow", True), "weight_used": 20},
            "geolocation":  {"score": score_row["geo_score"],          "reason": score_row["geo_reason"],          "consented": consent_map.get("geolocation", True), "weight_used": 12},
            "ecommerce":    {"score": score_row["ecommerce_score"],    "reason": score_row["ecommerce_reason"],    "consented": consent_map.get("ecommerce", True), "weight_used": 10},
            "merchant":     {"score": score_row["merchant_score"],     "reason": score_row["merchant_reason"],     "consented": consent_map.get("merchant", True), "weight_used": 5},
            "financial_commitment": {"score": score_row.get("financial_commitment_score", 0) if "financial_commitment_score" in score_row.keys() else 0, "reason": score_row.get("financial_commitment_reason", "") if "financial_commitment_reason" in score_row.keys() else "", "consented": consent_map.get("financial_commitment", True), "weight_used": 18},
            "psychometric": {"score": score_row["psychometric_score"], "reason": score_row["psychometric_reason"], "consented": True, "weight_used": 15},
        }
        
        # Parse weights_used JSON if available
        try:
            weights_used = json.loads(score_row["weights_used"]) if score_row["weights_used"] else {}
            for key in breakdown:
                agent_key = key.replace("_bill", "").replace("geo", "geolocation") if key == "geolocation" else key
                if agent_key in weights_used:
                    breakdown[key]["weight_used"] = round(weights_used[agent_key] * 100)
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

    return {
        "applicant": dict(applicant) if applicant else None,
        "score": score_data,
    }


# ── Applicant routes ───────────────────────────────────────────────────

@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new applicant. Stores encrypted PII, hashed Aadhaar."""
    if len(req.aadhaar_last4) != 4 or not req.aadhaar_last4.isdigit():
        raise HTTPException(status_code=400, detail="aadhaar_last4 must be exactly 4 digits")

    applicant_id = req.uid if req.uid else new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO applicants
               (id, name, phone_encrypted, email_encrypted, aadhaar_hash)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET 
                 name=excluded.name, 
                 phone_encrypted=excluded.phone_encrypted, 
                 email_encrypted=excluded.email_encrypted, 
                 aadhaar_hash=excluded.aadhaar_hash""",
            (
                applicant_id,
                req.name,
                encrypt_field(req.phone),
                encrypt_field(req.email),
                hash_aadhaar(req.aadhaar_last4),
            )
        )
        conn.commit()

    # Sync to MongoDB Atlas users
    from database_mongo import is_mongo_available, get_mongo_db
    if is_mongo_available():
        try:
            db = get_mongo_db()
            await db.users.update_one(
                {"email": req.email},
                {"$set": {
                    "phone": req.phone,
                    "aadhaar_last4": req.aadhaar_last4,
                }},
                upsert=True
            )
        except Exception as e:
            logger.warning(f"Failed to sync user detail to MongoDB during register: {e}")

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
        "financial_commitment": req.financial_commitment,
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
async def save_questionnaire(req: QuestionnaireRequest):
    """Save psychometric questionnaire responses to SQLite and MongoDB Atlas."""
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

    # Save to MongoDB Atlas
    from database_mongo import is_mongo_available, save_questionnaire_response_mongo
    if is_mongo_available():
        try:
            await save_questionnaire_response_mongo(req.applicant_id, req.answers)
        except Exception as e:
            logger.warning(f"Failed to save questionnaire responses to MongoDB: {e}")

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

        consent_rows = conn.execute(
            """SELECT source_name, consented FROM consent_logs
               WHERE applicant_id = ?
               ORDER BY timestamp DESC""",
            (applicant_id,)
        ).fetchall()

    consent_map = {}
    for cr in consent_rows:
        if cr["source_name"] not in consent_map:
            consent_map[cr["source_name"]] = bool(cr["consented"])

    score_data = None
    if score_row:
        breakdown = {
            "phone_bill":   {"score": score_row["phone_score"],        "reason": score_row["phone_reason"],        "consented": consent_map.get("phone_bill", consent_map.get("bill_consistency", True)), "weight_used": 20},
            "cashflow":     {"score": score_row["cashflow_score"],     "reason": score_row["cashflow_reason"],     "consented": consent_map.get("cashflow", True), "weight_used": 20},
            "geolocation":  {"score": score_row["geo_score"],          "reason": score_row["geo_reason"],          "consented": consent_map.get("geolocation", True), "weight_used": 12},
            "ecommerce":    {"score": score_row["ecommerce_score"],    "reason": score_row["ecommerce_reason"],    "consented": consent_map.get("ecommerce", True), "weight_used": 10},
            "merchant":     {"score": score_row["merchant_score"],     "reason": score_row["merchant_reason"],     "consented": consent_map.get("merchant", True), "weight_used": 5},
            "financial_commitment": {"score": score_row.get("financial_commitment_score", 0) if "financial_commitment_score" in score_row.keys() else 0, "reason": score_row.get("financial_commitment_reason", "") if "financial_commitment_reason" in score_row.keys() else "", "consented": consent_map.get("financial_commitment", True), "weight_used": 18},
            "psychometric": {"score": score_row["psychometric_score"], "reason": score_row["psychometric_reason"], "consented": True, "weight_used": 15},
        }
        # Parse weights_used JSON if available
        try:
            weights_used = json.loads(score_row["weights_used"]) if score_row["weights_used"] else {}
            for key in breakdown:
                agent_key = key.replace("_bill", "").replace("geo", "geolocation") if key == "geolocation" else key
                if agent_key in weights_used:
                    breakdown[key]["weight_used"] = round(weights_used[agent_key] * 100)
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

