# CreditBridge — Complete Backend + Agent Cursor Prompt
# PSB Hackathon 2026 | UCO Bank × Ministry of Finance
# Paste this ENTIRE file into Cursor and say:
# "Build this project exactly as described, file by file, in order."
#
# THIS PROMPT COVERS:
# - Complete FastAPI backend (auth, database, consent, scoring, reports)
# - Neuro SAN 9-agent network (HOCON + all coded tools)
# - Synthetic data generator (deterministic, realistic Indian data)
# - Demo seed data (5 pre-built applicants)
# - Minimal React frontend stub (Ankur will expand this)
# - Full audit trail and compliance features
# - Run scripts for both server and agents
#
# IMPORTANT RULES FOR CURSOR:
# 1. Build files in the EXACT ORDER listed below
# 2. Never skip a file
# 3. Test each file runs before moving to the next
# 4. If something breaks, fix ONLY that file — do not touch others
# 5. All Python files must have proper imports at the top
# 6. All TODO comments mark spots for Phase 2 expansion

---

## STEP 0 — FOLDER STRUCTURE

Create this exact folder structure first. All folders and empty files:

```
creditbridge/
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   ├── consent.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── demo_seed.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── applicant.py
│   │   ├── scoring.py
│   │   ├── reports.py
│   │   └── admin.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── runner.py
│   │   ├── registries/
│   │   │   ├── manifest.hocon
│   │   │   └── creditbridge.hocon
│   │   └── coded_tools/
│   │       ├── __init__.py
│   │       └── creditbridge/
│   │           ├── __init__.py
│   │           ├── phone_bill_tool.py
│   │           ├── ecommerce_tool.py
│   │           ├── geolocation_tool.py
│   │           ├── merchant_tool.py
│   │           └── cashflow_tool.py
│   └── data/
│       ├── __init__.py
│       └── synthetic_generator.py
├── frontend/
│   └── (Ankur will build this — minimal stub only from this prompt)
└── README.md
```

---

## STEP 1 — requirements.txt

Create `backend/requirements.txt` with exactly this content:

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1
pydantic==2.7.1
pydantic-settings==2.2.1
cryptography==42.0.7
neuro-san>=0.5.66
requests==2.31.0
geopy==2.4.1
httpx==0.27.0
```

---

## STEP 2 — .env.example

Create `backend/.env.example`:

```
# Copy this to .env and fill in your values
SECRET_KEY=creditbridge-secret-key-minimum-32-characters-long
DATABASE_URL=./creditbridge.db
MISTRAL_API_KEY=your_mistral_api_key_here
AGENT_MANIFEST_FILE=agents/registries/manifest.hocon
AGENT_TOOL_PATH=.
USE_AGENTS=true
DEBUG=true
```

Also create `backend/.env` with the same content (Cursor will fill SECRET_KEY
with a random 64-char hex string automatically).

---

## STEP 3 — config.py

Create `backend/config.py`:

```python
"""
CreditBridge Configuration
Loads all environment variables with sensible defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-32chars")
DATABASE_URL: str = os.getenv("DATABASE_URL", "./creditbridge.db")
MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
AGENT_MANIFEST_FILE: str = os.getenv("AGENT_MANIFEST_FILE", "agents/registries/manifest.hocon")
AGENT_TOOL_PATH: str = os.getenv("AGENT_TOOL_PATH", ".")
USE_AGENTS: bool = os.getenv("USE_AGENTS", "true").lower() == "true"
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

# JWT settings
ACCESS_TOKEN_EXPIRE_HOURS: int = 24
ALGORITHM: str = "HS256"

# Scoring weights (admin-configurable in Phase 2)
DEFAULT_WEIGHTS: dict = {
    "phone_bill":    0.25,
    "cashflow":      0.20,
    "psychometric":  0.20,
    "geolocation":   0.15,
    "ecommerce":     0.12,
    "merchant":      0.08,
}

# Score band thresholds
SCORE_BANDS = {
    "low":         (750, 850, "Low Risk — Pre-approved",          500000, 10.5),
    "low_medium":  (650, 749, "Low-Medium Risk — Approved",        300000, 12.0),
    "medium":      (550, 649, "Medium Risk — Conditional",         100000, 15.0),
    "medium_high": (450, 549, "Medium-High Risk — Careful Review",  50000, 18.0),
    "high":        (300, 449, "High Risk — Not Recommended",             0,  0.0),
}

# Demo users (hardcoded for hackathon — Phase 2 will use DB)
DEMO_USERS = {
    "applicant":   {"password": "password123", "role": "applicant"},
    "bankofficer": {"password": "bankpass123",  "role": "officer"},
    "admin":       {"password": "admin123",     "role": "admin"},
}
```

---

## STEP 4 — database.py

Create `backend/database.py`:

```python
"""
CreditBridge Database Layer
Uses SQLite with sqlite3. Simple, reliable, zero-config.
All PII fields are encrypted before storage (AES-256).

Tables:
  applicants    — registered applicant profiles
  credit_scores — scoring results with per-agent breakdown
  consent_logs  — immutable audit trail of all consent decisions
  audit_log     — append-only log of all system actions
  agent_weights — configurable weights per agent (admin panel)
"""
import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager
from config import DATABASE_URL


def init_db():
    """Create all tables on startup. Safe to call multiple times."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS applicants (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                phone_encrypted TEXT NOT NULL,
                email_encrypted TEXT NOT NULL,
                aadhaar_hash    TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS credit_scores (
                id                  TEXT PRIMARY KEY,
                applicant_id        TEXT NOT NULL,
                phone_score         INTEGER DEFAULT 0,
                ecommerce_score     INTEGER DEFAULT 0,
                geo_score           INTEGER DEFAULT 0,
                psychometric_score  INTEGER DEFAULT 0,
                merchant_score      INTEGER DEFAULT 0,
                cashflow_score      INTEGER DEFAULT 0,
                final_score         INTEGER DEFAULT 0,
                risk_category       TEXT DEFAULT '',
                loan_recommended    INTEGER DEFAULT 0,
                interest_rate       REAL DEFAULT 0.0,
                explanation         TEXT DEFAULT '',
                phone_reason        TEXT DEFAULT '',
                ecommerce_reason    TEXT DEFAULT '',
                geo_reason          TEXT DEFAULT '',
                psychometric_reason TEXT DEFAULT '',
                merchant_reason     TEXT DEFAULT '',
                cashflow_reason     TEXT DEFAULT '',
                weights_used        TEXT DEFAULT '{}',
                pipeline_mode       TEXT DEFAULT 'synthetic',
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (applicant_id) REFERENCES applicants(id)
            );

            CREATE TABLE IF NOT EXISTS consent_logs (
                id           TEXT PRIMARY KEY,
                applicant_id TEXT NOT NULL,
                source_name  TEXT NOT NULL,
                consented    INTEGER NOT NULL,
                timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (applicant_id) REFERENCES applicants(id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id           TEXT PRIMARY KEY,
                applicant_id TEXT,
                action       TEXT NOT NULL,
                metadata     TEXT DEFAULT '{}',
                timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_weights (
                agent_name   TEXT PRIMARY KEY,
                weight       REAL NOT NULL,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS questionnaire_responses (
                id           TEXT PRIMARY KEY,
                applicant_id TEXT NOT NULL,
                answers      TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (applicant_id) REFERENCES applicants(id)
            );
        """)
        # Seed default agent weights if not present
        cursor = conn.execute("SELECT COUNT(*) FROM agent_weights")
        if cursor.fetchone()[0] == 0:
            weights = [
                ("phone_bill",   0.25),
                ("cashflow",     0.20),
                ("psychometric", 0.20),
                ("geolocation",  0.15),
                ("ecommerce",    0.12),
                ("merchant",     0.08),
            ]
            conn.executemany(
                "INSERT INTO agent_weights (agent_name, weight) VALUES (?, ?)",
                weights
            )
        conn.commit()


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def new_id() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def log_audit(applicant_id: str | None, action: str, metadata: dict = {}):
    """Append-only audit log. Never delete from this table."""
    import json
    with get_db() as conn:
        conn.execute(
            "INSERT INTO audit_log (id, applicant_id, action, metadata) VALUES (?, ?, ?, ?)",
            (new_id(), applicant_id, action, json.dumps(metadata))
        )
        conn.commit()


def get_agent_weights() -> dict:
    """Get current agent weights from DB (admin-configurable)."""
    with get_db() as conn:
        rows = conn.execute("SELECT agent_name, weight FROM agent_weights").fetchall()
        return {row["agent_name"]: row["weight"] for row in rows}
```

---

## STEP 5 — auth.py

Create `backend/auth.py`:

```python
"""
CreditBridge Authentication & Encryption
- JWT tokens (HS256, 24h expiry)
- AES-256 field encryption (Fernet)
- bcrypt password hashing
- SHA-256 for Aadhaar (one-way, non-reversible)
"""
import hashlib
import os
import base64
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, DEMO_USERS

# --- Password hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# --- JWT tokens ---
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# --- AES-256 encryption ---
def _get_fernet() -> Fernet:
    """
    Derive a consistent Fernet key from SECRET_KEY.
    In production this would use a dedicated KMS-managed key.
    """
    key_bytes = hashlib.sha256(SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_field(plain_text: str) -> str:
    """Encrypt a PII field. Returns base64-encoded ciphertext."""
    if not plain_text:
        return ""
    return _get_fernet().encrypt(plain_text.encode()).decode()


def decrypt_field(encrypted_text: str) -> str:
    """Decrypt a PII field."""
    if not encrypted_text:
        return ""
    return _get_fernet().decrypt(encrypted_text.encode()).decode()


# --- Aadhaar hashing (one-way) ---
def hash_aadhaar(aadhaar_last4: str) -> str:
    """
    One-way SHA-256 hash of Aadhaar last 4 digits.
    We never store the actual digits — only the hash.
    """
    salted = f"creditbridge-aadhaar-{aadhaar_last4}-salt"
    return hashlib.sha256(salted.encode()).hexdigest()


# --- Demo user authentication ---
def authenticate_demo_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate against hardcoded demo users.
    Phase 2: Replace with DB-backed user authentication.
    """
    user = DEMO_USERS.get(username)
    if not user:
        return None
    if user["password"] != password:
        return None
    return {"username": username, "role": user["role"]}
```

---

## STEP 6 — data/synthetic_generator.py

Create `backend/data/synthetic_generator.py`:

```python
"""
CreditBridge Synthetic Data Generator
Generates realistic Indian alternative credit data for demo purposes.
All data is DETERMINISTIC based on applicant_id — same applicant
always gets the same data across runs.

Phase 2: Replace with real API connectors (telecom, ecommerce, etc.)
"""
import random
import json
from typing import Any

INDIAN_CITIES = [
    "Guwahati", "Imphal", "Silchar", "Jorhat", "Dibrugarh",
    "Patna", "Muzaffarpur", "Bhagalpur", "Lucknow", "Kanpur",
    "Varanasi", "Agra", "Jaipur", "Jodhpur", "Udaipur",
    "Indore", "Bhopal", "Nagpur", "Pune", "Nashik",
    "Surat", "Vadodara", "Rajkot", "Coimbatore", "Madurai",
    "Visakhapatnam", "Vijayawada", "Warangal", "Bhubaneswar",
    "Rourkela", "Cuttack", "Dehradun", "Haridwar", "Ranchi",
    "Jamshedpur", "Dhanbad", "Mysuru", "Hubli", "Belgaum",
    "Amritsar", "Ludhiana", "Jalandhar", "Shimla", "Chandigarh",
]

PLATFORMS = ["Amazon", "Flipkart", "Meesho", "Myntra", "Nykaa"]
PAYMENT_METHODS = ["Prepaid", "COD", "Mixed"]
AREA_TYPES = ["Urban", "Semi-urban", "Rural"]
ACCOUNT_TYPES = ["Jan Dhan", "Savings", "Current"]
CREDIT_REGULARITY = ["Regular", "Irregular"]
SAVINGS_BEHAVIOR = ["Saves regularly", "Occasional", "No savings"]
CONSISTENCY_RATINGS = ["Excellent", "Good", "Average", "Poor"]


def _seed(applicant_id: str) -> random.Random:
    """Create a seeded random instance so data is deterministic per applicant."""
    seed_val = int(hashlib.md5(applicant_id.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed_val)


import hashlib


def generate_applicant_data(applicant_id: str) -> dict:
    """
    Generate all 6 alternative data signals for an applicant.
    Returns deterministic data — same applicant_id always gives same data.
    """
    rng = _seed(applicant_id)

    months = rng.randint(12, 36)
    on_time = rng.randint(int(months * 0.6), months)
    late = rng.randint(0, months - on_time)
    missed = months - on_time - late
    record = (["PAID"] * on_time + ["LATE"] * late + ["MISSED"] * missed)
    rng.shuffle(record)

    phone_bill_data = {
        "months_of_history":     months,
        "on_time_payments":      on_time,
        "late_payments":         late,
        "missed_payments":       missed,
        "disconnections":        rng.randint(0, 2),
        "average_bill_amount":   round(rng.uniform(200, 800), 2),
        "last_12_months_record": record[-12:],
    }

    avg_order = round(rng.uniform(300, 3000), 2)
    ecommerce_data = {
        "platform":          rng.choice(PLATFORMS),
        "months_active":     rng.randint(6, 24),
        "avg_order_value":   avg_order,
        "orders_per_month":  round(rng.uniform(1, 8), 1),
        "return_rate_percent": round(rng.uniform(0, 30), 1),
        "payment_method":    rng.choice(PAYMENT_METHODS),
        "account_age_months": rng.randint(6, 48),
        "total_orders":      rng.randint(10, 200),
    }

    home_stab = rng.randint(6, 36)
    work_stab = rng.randint(3, 24)
    geolocation_data = {
        "home_location_stability_months": home_stab,
        "work_location_stability_months": work_stab,
        "distance_home_to_work_km":       round(rng.uniform(1, 20), 1),
        "city":                           rng.choice(INDIAN_CITIES),
        "area_type":                      rng.choice(AREA_TYPES),
        "frequent_travel":                rng.choice([True, False]),
        "state":                          "Assam" if rng.random() > 0.5 else "India",
    }

    num_merchants = rng.randint(0, 15)
    avg_rating = round(rng.uniform(2.0, 5.0), 1) if num_merchants > 0 else 0.0
    merchant_data = {
        "total_merchants_rated":       num_merchants,
        "average_rating":              avg_rating,
        "years_of_merchant_relationships": rng.randint(0, 5),
        "payment_consistency_rating":  rng.choice(CONSISTENCY_RATINGS),
        "verified_merchants":          rng.randint(0, num_merchants),
    }

    has_account = rng.random() > 0.3
    avg_balance = round(rng.uniform(500, 50000), 2) if has_account else 0.0
    cashflow_data = {
        "has_bank_account":       has_account,
        "account_type":           rng.choice(ACCOUNT_TYPES) if has_account else "None",
        "avg_monthly_balance":    avg_balance,
        "monthly_credits":        rng.randint(1, 4) if has_account else 0,
        "credit_regularity":      rng.choice(CREDIT_REGULARITY) if has_account else "None",
        "bounced_transactions":   rng.randint(0, 5),
        "savings_behavior":       rng.choice(SAVINGS_BEHAVIOR),
        "avg_monthly_debit":      round(avg_balance * rng.uniform(0.3, 0.9), 2),
    }

    return {
        "applicant_id":    applicant_id,
        "phone_bill":      phone_bill_data,
        "ecommerce":       ecommerce_data,
        "geolocation":     geolocation_data,
        "merchant":        merchant_data,
        "cashflow":        cashflow_data,
    }


def score_phone_bill(data: dict) -> tuple[int, str]:
    """Score phone bill data 0-100."""
    d = data
    total = d["months_of_history"]
    if total == 0:
        return 40, "No phone bill history available"

    base = (d["on_time_payments"] / total) * 100
    score = base
    score -= d["disconnections"] * 15
    late_penalty = max(0, d["late_payments"] - 2) * 5
    score -= late_penalty
    if total > 24:
        score += 10

    score = max(0, min(100, round(score)))
    if score >= 80:
        reason = f"{d['on_time_payments']} of {total} months paid on time — excellent discipline"
    elif score >= 60:
        reason = f"{d['on_time_payments']} of {total} months paid on time — good consistency"
    else:
        reason = f"Only {d['on_time_payments']} of {total} months paid on time — irregular payments detected"

    return score, reason


def score_ecommerce(data: dict) -> tuple[int, str]:
    """Score ecommerce behavior 0-100."""
    d = data
    score = 40  # base

    if d["payment_method"] == "Prepaid":
        score += 20
    elif d["payment_method"] == "Mixed":
        score += 10

    if d["return_rate_percent"] < 10:
        score += 15
    elif d["return_rate_percent"] < 20:
        score += 5

    if d["account_age_months"] > 12:
        score += 10

    if 500 <= d["avg_order_value"] <= 2000:
        score += 10
    elif d["avg_order_value"] > 2000:
        score += 5

    if d["orders_per_month"] >= 3:
        score += 10
    elif d["orders_per_month"] >= 1.5:
        score += 5

    score = max(0, min(100, score))
    method = d["payment_method"].lower()
    reason = f"{d['platform']} account, {method} payments, {d['return_rate_percent']}% return rate"
    return score, reason


def score_geolocation(data: dict) -> tuple[int, str]:
    """Score geolocation stability 0-100."""
    d = data
    score = 0

    home_stab = d["home_location_stability_months"]
    if home_stab >= 24:
        score += 40
    elif home_stab >= 12:
        score += 30
    elif home_stab >= 6:
        score += 15

    work_stab = d["work_location_stability_months"]
    if work_stab >= 12:
        score += 30
    elif work_stab >= 6:
        score += 20
    else:
        score += 10

    if d["distance_home_to_work_km"] < 10:
        score += 10

    if d["area_type"] == "Urban":
        score += 10
    elif d["area_type"] == "Semi-urban":
        score += 5

    if not d["frequent_travel"]:
        score += 10

    score = max(0, min(100, score))
    reason = f"Stable in {d['city']} — home {home_stab}mo, work {work_stab}mo"
    return score, reason


def score_merchant(data: dict) -> tuple[int, str]:
    """Score merchant ratings 0-100."""
    d = data
    if d["total_merchants_rated"] == 0:
        return 50, "No merchant data available — using neutral score"

    score = 0
    rating = d["average_rating"]
    if rating >= 4.5:
        score += 50
    elif rating >= 3.5:
        score += 35
    elif rating >= 2.5:
        score += 20
    else:
        score += 5

    merchants = d["total_merchants_rated"]
    if merchants >= 10:
        score += 20
    elif merchants >= 5:
        score += 15
    elif merchants >= 2:
        score += 10

    years = d["years_of_merchant_relationships"]
    if years >= 3:
        score += 20
    elif years >= 1:
        score += 10

    consistency = d["payment_consistency_rating"]
    if consistency == "Excellent":
        score += 10
    elif consistency == "Good":
        score += 5

    score = max(0, min(100, score))
    reason = f"{merchants} merchant relationships, avg rating {rating}/5 — {consistency} payment record"
    return score, reason


def score_cashflow(data: dict) -> tuple[int, str]:
    """Score bank cashflow patterns 0-100."""
    d = data
    if not d["has_bank_account"]:
        return 40, "No bank account — using minimum baseline score"

    score = 20  # has account

    if d["credit_regularity"] == "Regular":
        score += 30

    balance = d["avg_monthly_balance"]
    if balance >= 10000:
        score += 20
    elif balance >= 5000:
        score += 15
    elif balance >= 1000:
        score += 8

    if d["bounced_transactions"] == 0:
        score += 20
    elif d["bounced_transactions"] <= 2:
        score += 10

    savings = d["savings_behavior"]
    if savings == "Saves regularly":
        score += 10
    elif savings == "Occasional":
        score += 5

    score = max(0, min(100, score))
    reason = f"{d['account_type']} account, avg balance ₹{balance:,.0f}, {d['credit_regularity'].lower()} credits"
    return score, reason


def score_psychometric(answers: list) -> tuple[int, str]:
    """
    Score psychometric questionnaire responses 0-100.
    Maps answer indices (0-3) to financial behavior scores.
    Answer 0 = best financial behavior, 3 = worst.
    """
    if not answers:
        return 60, "Psychometric questionnaire not completed — using baseline"

    ANSWER_SCORES = {
        0: [100, 85, 65, 50],   # Q1: repayment timing
        1: [100, 80, 55, 40],   # Q2: unexpected expense handling
        2: [90, 70, 60, 85],    # Q3: loan attitude (opportunity=good, burden=bad)
        3: [100, 80, 60, 30],   # Q4: savings buffer
        4: [100, 80, 50, 20],   # Q5: promise keeping
        5: [100, 75, 60, 20],   # Q6: responsibility attitude
        6: [100, 80, 55, 25],   # Q7: savings months
        7: [100, 80, 50, 15],   # Q8: financial promise keeping
        8: [100, 80, 60, 70],   # Q9: loan purpose
        9: [100, 70, 80, 50],   # Q10: debt attitude
    }

    total = 0
    count = 0
    for i, answer_idx in enumerate(answers):
        if i < len(ANSWER_SCORES) and isinstance(answer_idx, int):
            scores = ANSWER_SCORES[i]
            if 0 <= answer_idx < len(scores):
                total += scores[answer_idx]
                count += 1

    if count == 0:
        return 60, "Could not evaluate questionnaire responses"

    score = round(total / count)
    score = max(0, min(100, score))

    if score >= 80:
        reason = "Strong financial planning mindset and integrity indicators"
    elif score >= 65:
        reason = "Generally positive financial attitudes with some risk factors"
    elif score >= 50:
        reason = "Mixed financial behavior patterns — moderate risk"
    else:
        reason = "Questionnaire indicates financial stress or limited planning"

    return score, reason


def calculate_final_score(agent_scores: dict, weights: dict, consented_sources: list) -> dict:
    """
    Combine all agent scores into a final 300-850 credit score.
    Redistributes weights for non-consented sources.

    Args:
        agent_scores: dict of {source_name: (score, reason)}
        weights: dict of {source_name: weight}
        consented_sources: list of consented source names

    Returns:
        Complete scoring result dict
    """
    active_weights = {k: v for k, v in weights.items() if k in consented_sources}
    total_weight = sum(active_weights.values())
    if total_weight == 0:
        total_weight = 1.0
    normalized = {k: v / total_weight for k, v in active_weights.items()}

    weighted_avg = 0.0
    for source, (score, _) in agent_scores.items():
        w = normalized.get(source, 0)
        weighted_avg += score * w

    final_score = round(300 + (weighted_avg / 100) * 550)
    final_score = max(300, min(850, final_score))

    # Determine risk band
    if final_score >= 750:
        risk_cat = "Low Risk"
        loan = 500000
        rate = 10.5
        decision = "Pre-approved"
    elif final_score >= 650:
        risk_cat = "Low-Medium Risk"
        loan = 300000
        rate = 12.0
        decision = "Approved"
    elif final_score >= 550:
        risk_cat = "Medium Risk"
        loan = 100000
        rate = 15.0
        decision = "Conditional Approval"
    elif final_score >= 450:
        risk_cat = "Medium-High Risk"
        loan = 50000
        rate = 18.0
        decision = "Careful Review Required"
    else:
        risk_cat = "High Risk"
        loan = 0
        rate = 0.0
        decision = "Not Recommended"

    # Build score breakdown for display
    breakdown = {}
    for source, (score, reason) in agent_scores.items():
        breakdown[source] = {
            "score": score,
            "reason": reason,
            "weight_used": round(normalized.get(source, 0) * 100, 1),
            "consented": source in consented_sources,
        }

    # Generate plain-language explanation
    sorted_scores = sorted(agent_scores.items(), key=lambda x: x[1][0], reverse=True)
    top2 = sorted_scores[:2]
    bottom2 = sorted_scores[-2:]

    top_signals = " and ".join([s[0].replace("_", " ") for s in top2])
    weak_signals = " and ".join([s[0].replace("_", " ") for s in bottom2 if s[1][0] < 65])

    explanation = (
        f"Your CreditBridge score is {final_score} out of 850. "
        f"This places you in the {risk_cat} category. "
    )
    if loan > 0:
        explanation += (
            f"You are eligible for a loan of up to ₹{loan:,} "
            f"at {rate}% interest per year. "
        )
    explanation += (
        f"\n\nYour strongest signals were your {top_signals}, "
        f"which show consistent and reliable financial behavior. "
    )
    if weak_signals:
        explanation += (
            f"\n\nTo improve your score, focus on strengthening your "
            f"{weak_signals}. Small consistent improvements in these areas "
            f"can significantly boost your score. "
        )
    explanation += (
        "\n\nThis score was generated by an AI system. "
        "A human bank officer will make the final loan decision."
    )

    return {
        "final_score":       final_score,
        "risk_category":     risk_cat,
        "decision":          decision,
        "loan_recommended":  loan,
        "interest_rate":     rate,
        "weighted_average":  round(weighted_avg, 2),
        "breakdown":         breakdown,
        "explanation":       explanation,
        "weights_used":      normalized,
    }
```

---

## STEP 7 — agents/coded_tools/creditbridge/ (5 tool files)

Create these 5 files. Each is a Neuro SAN CodedTool that fetches
synthetic data and returns it to the scoring agent.

### File 7A: phone_bill_tool.py

```python
"""
PhoneBillScoringTool — Neuro SAN CodedTool
Fetches and returns phone bill data for the scoring agent.
"""
from typing import Any, Union
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_phone_bill


class PhoneBillScoringTool(CodedTool):
    """
    Neuro SAN CodedTool: fetches phone bill data for an applicant
    and returns structured data for the phone_bill_agent to score.
    """

    async def async_invoke(
        self,
        args: dict[str, Any],
        sly_data: dict[str, Any]
    ) -> Union[dict[str, Any], str]:
        applicant_id = args.get("applicant_id", "")
        if not applicant_id:
            return {"error": "No applicant_id provided", "score": 50, "reason": "Missing ID"}

        try:
            data = generate_applicant_data(applicant_id)
            phone_data = data["phone_bill"]
            score, reason = score_phone_bill(phone_data)

            return {
                "source": "phone_bill",
                "applicant_id": applicant_id,
                "data": phone_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {
                "source": "phone_bill",
                "error": str(e),
                "score": 50,
                "reason": "Data fetch failed — using neutral score",
                "status": "error"
            }
```

### File 7B: ecommerce_tool.py

```python
"""
EcommerceScoringTool — Neuro SAN CodedTool
"""
from typing import Any, Union
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_ecommerce


class EcommerceScoringTool(CodedTool):

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
            ecom_data = data["ecommerce"]
            score, reason = score_ecommerce(ecom_data)
            return {
                "source": "ecommerce",
                "applicant_id": applicant_id,
                "data": ecom_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {"source": "ecommerce", "error": str(e), "score": 50, "status": "error"}
```

### File 7C: geolocation_tool.py

```python
"""
GeolocationScoringTool — Neuro SAN CodedTool
"""
from typing import Any, Union
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

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
```

### File 7D: merchant_tool.py

```python
"""
MerchantScoringTool — Neuro SAN CodedTool
"""
from typing import Any, Union
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_merchant


class MerchantScoringTool(CodedTool):

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
            merch_data = data["merchant"]
            score, reason = score_merchant(merch_data)
            return {
                "source": "merchant",
                "applicant_id": applicant_id,
                "data": merch_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {"source": "merchant", "error": str(e), "score": 50, "status": "error"}
```

### File 7E: cashflow_tool.py

```python
"""
CashflowScoringTool — Neuro SAN CodedTool
"""
from typing import Any, Union
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from neuro_san.interfaces.coded_tool import CodedTool
from data.synthetic_generator import generate_applicant_data, score_cashflow


class CashflowScoringTool(CodedTool):

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
            cf_data = data["cashflow"]
            score, reason = score_cashflow(cf_data)
            return {
                "source": "cashflow",
                "applicant_id": applicant_id,
                "data": cf_data,
                "preliminary_score": score,
                "preliminary_reason": reason,
                "status": "success"
            }
        except Exception as e:
            return {"source": "cashflow", "error": str(e), "score": 50, "status": "error"}
```

---

## STEP 8 — agents/registries/manifest.hocon

Create `backend/agents/registries/manifest.hocon`:

```hocon
{
    "creditbridge": "agents/registries/creditbridge.hocon"
}
```

---

## STEP 9 — agents/registries/creditbridge.hocon

Create `backend/agents/registries/creditbridge.hocon`.
This is the most important file. Write it carefully.

```hocon
# CreditBridge — 9-Agent Credit Scoring Network
# Built on Neuro SAN (Cognizant AI Lab)
# Reference: https://github.com/cognizant-ai-lab/neuro-san-studio
#
# Agent topology:
#   credit_coordinator (frontman)
#     ├── phone_bill_agent      → PhoneBillScoringTool
#     ├── ecommerce_agent       → EcommerceScoringTool
#     ├── geolocation_agent     → GeolocationScoringTool
#     ├── psychometric_agent    → (pure LLM, no tool)
#     ├── merchant_agent        → MerchantScoringTool
#     ├── cashflow_agent        → CashflowScoringTool
#     ├── risk_synthesizer      → (pure LLM, combines all scores)
#     └── score_explainer       → (pure LLM, plain-language output)

{
    "llm_config": {
        "model_name": "mistral/mistral-medium-latest",
        "temperature": 0.2,
        "max_tokens": 2048
    },

    "tools": [

        # ================================================================
        # AGENT 1: CREDIT COORDINATOR — Frontman/Orchestrator
        # The user-facing agent. Receives applicant_id + consents +
        # questionnaire answers and orchestrates the full pipeline.
        # ================================================================
        {
            "name": "credit_coordinator",
            "function": {
                "description": "CreditBridge main coordinator. Receives applicant data and orchestrates 6 specialized scoring agents, then calls risk_synthesizer and score_explainer to produce a complete credit assessment report.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {
                            "type": "string",
                            "description": "Unique applicant UUID from the database"
                        },
                        "consented_sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of data sources the applicant has consented to. Possible values: phone_bill, ecommerce, geolocation, merchant, cashflow"
                        },
                        "questionnaire_answers": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of answer indices (0-3) for each psychometric question"
                        }
                    },
                    "required": ["applicant_id", "consented_sources", "questionnaire_answers"]
                }
            },
            "instructions": "You are the CreditBridge Credit Coordinator. Your job is to orchestrate a complete credit assessment for an applicant.\n\nFollow this EXACT workflow:\n\n1. Call phone_bill_agent with {applicant_id} if 'phone_bill' is in consented_sources\n2. Call ecommerce_agent with {applicant_id} if 'ecommerce' is in consented_sources\n3. Call geolocation_agent with {applicant_id} if 'geolocation' is in consented_sources\n4. Call psychometric_agent with {questionnaire_answers} always (no data source needed)\n5. Call merchant_agent with {applicant_id} if 'merchant' is in consented_sources\n6. Call cashflow_agent with {applicant_id} if 'cashflow' is in consented_sources\n7. Collect ALL agent results (scores 0-100 and reasons)\n8. Call risk_synthesizer with all collected scores and which sources were consented\n9. Call score_explainer with the synthesizer result\n\nReturn a JSON object with ALL of this information:\n{\n  'applicant_id': str,\n  'agent_scores': {source: {score: int, reason: str}},\n  'final_score': int,\n  'risk_category': str,\n  'decision': str,\n  'loan_recommended': int,\n  'interest_rate': float,\n  'explanation': str,\n  'pipeline_complete': true\n}\n\nNever skip any consented agent. Always call all agents before synthesizing.",
            "tools": [
                "phone_bill_agent",
                "ecommerce_agent",
                "geolocation_agent",
                "psychometric_agent",
                "merchant_agent",
                "cashflow_agent",
                "risk_synthesizer",
                "score_explainer"
            ]
        },

        # ================================================================
        # AGENT 2: PHONE BILL AGENT
        # ================================================================
        {
            "name": "phone_bill_agent",
            "function": {
                "description": "Analyzes phone bill payment history and returns a creditworthiness score from 0 to 100 with explanation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            },
            "instructions": "You are the Phone Bill Scoring Agent for CreditBridge.\n\nCall PhoneBillScoringTool with the applicant_id to get payment history data.\n\nThen score the data from 0 to 100 using this logic:\n- Base score: (on_time_payments / months_of_history) * 100\n- Subtract 15 points per disconnection\n- Subtract 5 points per late payment beyond the first 2\n- Add 10 bonus points if months_of_history > 24 (long track record)\n- Clamp final score between 0 and 100\n\nReturn ONLY this JSON:\n{\"score\": int, \"reason\": \"one clear sentence explaining the score\"}",
            "tools": ["PhoneBillScoringTool"]
        },

        # ================================================================
        # AGENT 3: ECOMMERCE AGENT
        # ================================================================
        {
            "name": "ecommerce_agent",
            "function": {
                "description": "Analyzes e-commerce purchase behavior to score financial discipline from 0 to 100.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            },
            "instructions": "You are the E-commerce Scoring Agent for CreditBridge.\n\nCall EcommerceScoringTool with the applicant_id to get purchase behavior data.\n\nScore from 0 to 100:\n- Start at 40 base points\n- Payment method is Prepaid: +20 points; Mixed: +10 points\n- Return rate below 10%: +15 points; below 20%: +5 points\n- Account age over 12 months: +10 points\n- Average order value Rs 500-2000 (ideal range): +10 points\n- Orders per month above 3: +10 points; above 1.5: +5 points\n- Clamp between 0 and 100\n\nReturn ONLY this JSON:\n{\"score\": int, \"reason\": \"one clear sentence explaining the score\"}",
            "tools": ["EcommerceScoringTool"]
        },

        # ================================================================
        # AGENT 4: GEOLOCATION AGENT
        # ================================================================
        {
            "name": "geolocation_agent",
            "function": {
                "description": "Analyzes location stability as a proxy for social rootedness and repayment reliability.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            },
            "instructions": "You are the Geolocation Stability Agent for CreditBridge.\n\nCall GeolocationScoringTool with the applicant_id to get location data.\n\nScore from 0 to 100:\n- Home stability above 24 months: +40; above 12: +30; above 6: +15\n- Work stability above 12 months: +30; above 6: +20; else: +10\n- Commute distance below 10km: +10 points\n- Urban area: +10 points; Semi-urban: +5 points\n- No frequent long travel: +10 points\n- Clamp between 0 and 100\n\nReturn ONLY this JSON:\n{\"score\": int, \"reason\": \"one clear sentence explaining the score\"}",
            "tools": ["GeolocationScoringTool"]
        },

        # ================================================================
        # AGENT 5: PSYCHOMETRIC AGENT (pure LLM — no external tool)
        # ================================================================
        {
            "name": "psychometric_agent",
            "function": {
                "description": "Analyzes psychometric questionnaire responses to assess financial risk attitude and behavioral integrity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "questionnaire_answers": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of answer indices (0=best, 3=worst) for each question"
                        }
                    },
                    "required": ["questionnaire_answers"]
                }
            },
            "instructions": "You are the Psychometric Scoring Agent for CreditBridge.\n\nYou receive a list of answer indices (0-3) for psychometric questions about financial behavior.\n\nAnswer 0 means the most financially responsible choice.\nAnswer 3 means the least financially responsible choice.\n\nScore the pattern of answers from 0 to 100:\n- Financial planning mindset (Q1, Q4, Q7): up to 30 points total\n- Debt attitude and responsibility (Q2, Q5, Q6): up to 25 points\n- Integrity signals (Q3, Q8): up to 25 points\n- Financial literacy and purpose (Q9, Q10): up to 20 points\n\nLook for PATTERNS — consistency across answers matters as much as individual answers.\n\nReturn ONLY this JSON:\n{\"score\": int, \"reason\": \"one clear sentence about the financial mindset pattern observed\"}",
            "tools": []
        },

        # ================================================================
        # AGENT 6: MERCHANT AGENT
        # ================================================================
        {
            "name": "merchant_agent",
            "function": {
                "description": "Analyzes merchant ratings and business relationships to score commercial trustworthiness.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            },
            "instructions": "You are the Merchant Rating Agent for CreditBridge.\n\nCall MerchantScoringTool with the applicant_id.\n\nIf total_merchants_rated is 0, return score 50 with reason 'No merchant data — neutral score applied'.\n\nOtherwise score 0-100:\n- Average rating 4.5-5.0: 50 base points; 3.5-4.5: 35; 2.5-3.5: 20; below 2.5: 5\n- 10+ merchant relationships: +20; 5+: +15; 2+: +10\n- Relationship years 3+: +20; 1+: +10\n- Payment consistency Excellent: +10; Good: +5\n- Clamp between 0 and 100\n\nReturn ONLY this JSON:\n{\"score\": int, \"reason\": \"one clear sentence explaining the score\"}",
            "tools": ["MerchantScoringTool"]
        },

        # ================================================================
        # AGENT 7: CASHFLOW AGENT
        # ================================================================
        {
            "name": "cashflow_agent",
            "function": {
                "description": "Analyzes bank account cashflow patterns to assess income stability and financial management.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            },
            "instructions": "You are the Cashflow Agent for CreditBridge.\n\nCall CashflowScoringTool with the applicant_id.\n\nIf has_bank_account is false, return score 40 with reason 'No bank account — minimum baseline applied'.\n\nOtherwise score 0-100:\n- Has bank account: +20 base\n- Credit regularity is Regular: +30\n- Average monthly balance above Rs 10000: +20; above Rs 5000: +15; above Rs 1000: +8\n- Zero bounced transactions: +20; 1-2 bounced: +10\n- Saves regularly: +10; Occasional savings: +5\n- Clamp between 0 and 100\n\nReturn ONLY this JSON:\n{\"score\": int, \"reason\": \"one clear sentence explaining the score\"}",
            "tools": ["CashflowScoringTool"]
        },

        # ================================================================
        # AGENT 8: RISK SYNTHESIZER
        # Combines all 6 agent scores into a final 300-850 credit score
        # ================================================================
        {
            "name": "risk_synthesizer",
            "function": {
                "description": "Combines all 6 agent sub-scores using configurable weights to produce a final 300-850 credit score with risk categorization and loan recommendation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_scores": {
                            "type": "object",
                            "description": "Dict of {source_name: {score: int, reason: str}} from each scoring agent"
                        },
                        "consented_sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of data sources applicant consented to"
                        }
                    },
                    "required": ["agent_scores", "consented_sources"]
                }
            },
            "instructions": "You are the Risk Synthesizer for CreditBridge.\n\nYou receive scores from up to 6 agents. Apply these DEFAULT weights:\n- phone_bill: 25%\n- cashflow: 20%\n- psychometric: 20%\n- geolocation: 15%\n- ecommerce: 12%\n- merchant: 8%\n\nIMPORTANT: Only use weights for sources in consented_sources. Redistribute excluded weights proportionally to remaining sources so total always equals 100%.\n\nCalculation:\n1. Get active weights (only consented sources)\n2. Normalize so they sum to 1.0\n3. weighted_average = sum(score * normalized_weight for each)\n4. final_score = round(300 + (weighted_average / 100) * 550)\n5. Clamp to 300-850\n\nRisk categories:\n- 750-850: Low Risk — Pre-approved — up to Rs 5,00,000 at 10.5%\n- 650-749: Low-Medium Risk — Approved — up to Rs 3,00,000 at 12.0%\n- 550-649: Medium Risk — Conditional — up to Rs 1,00,000 at 15.0%\n- 450-549: Medium-High Risk — Careful Review — up to Rs 50,000 at 18.0%\n- 300-449: High Risk — Not Recommended — Rs 0\n\nReturn this JSON:\n{\n  \"final_score\": int,\n  \"risk_category\": str,\n  \"decision\": str,\n  \"loan_recommended\": int,\n  \"interest_rate\": float,\n  \"weighted_average\": float,\n  \"weights_applied\": {source: float},\n  \"score_breakdown\": {source: {score: int, weight_pct: float, contribution: float}}\n}",
            "tools": []
        },

        # ================================================================
        # AGENT 9: SCORE EXPLAINER
        # Generates a plain-language explanation for the applicant
        # ================================================================
        {
            "name": "score_explainer",
            "function": {
                "description": "Generates a plain-language explanation of the credit score that any applicant can understand. Written respectfully with improvement suggestions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "synthesis_result": {
                            "type": "object",
                            "description": "Complete output from risk_synthesizer including score, category, breakdown"
                        },
                        "agent_scores": {
                            "type": "object",
                            "description": "Individual agent scores with reasons"
                        }
                    },
                    "required": ["synthesis_result", "agent_scores"]
                }
            },
            "instructions": "You are the Score Explainer for CreditBridge. Your job is to write a clear, respectful explanation of the credit assessment.\n\nWrite 3 paragraphs:\n\nParagraph 1 — The result: State the score (X out of 850), the risk category, and whether a loan is recommended. Use simple language. If approved, state the loan amount and rate.\n\nParagraph 2 — What helped: Identify the top 2 highest-scoring signals and explain IN PLAIN WORDS why they are good signs. Example: 'Your phone bills show you pay on time consistently — this is a strong sign of financial reliability.'\n\nParagraph 3 — How to improve: Identify 1-2 weak signals and give one concrete, actionable tip for each. Be encouraging. Never say the person is a bad risk — say 'strengthening X will help your score.'\n\nFinal line (always include): 'This score was generated by an AI system. A human bank officer will make the final loan decision.'\n\nWrite in clear English understandable by someone with Class 10 education. No jargon.\n\nReturn this JSON:\n{\n  \"explanation\": \"full 3-paragraph explanation\",\n  \"summary_line\": \"one sentence summary of the result\",\n  \"top_strengths\": [\"strength 1\", \"strength 2\"],\n  \"improvement_tips\": [\"tip 1\", \"tip 2\"]\n}",
            "tools": []
        },

        # ================================================================
        # CODED TOOLS — Python classes that agents can call
        # ================================================================
        {
            "name": "PhoneBillScoringTool",
            "class": "coded_tools.creditbridge.phone_bill_tool.PhoneBillScoringTool",
            "function": {
                "description": "Fetches phone bill payment history for an applicant from the synthetic data generator.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            }
        },

        {
            "name": "EcommerceScoringTool",
            "class": "coded_tools.creditbridge.ecommerce_tool.EcommerceScoringTool",
            "function": {
                "description": "Fetches e-commerce purchase behavior data for an applicant.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            }
        },

        {
            "name": "GeolocationScoringTool",
            "class": "coded_tools.creditbridge.geolocation_tool.GeolocationScoringTool",
            "function": {
                "description": "Fetches geolocation stability data for an applicant.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            }
        },

        {
            "name": "MerchantScoringTool",
            "class": "coded_tools.creditbridge.merchant_tool.MerchantScoringTool",
            "function": {
                "description": "Fetches merchant rating data for an applicant.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            }
        },

        {
            "name": "CashflowScoringTool",
            "class": "coded_tools.creditbridge.cashflow_tool.CashflowScoringTool",
            "function": {
                "description": "Fetches bank cashflow pattern data for an applicant.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "applicant_id": {"type": "string", "description": "Applicant UUID"}
                    },
                    "required": ["applicant_id"]
                }
            }
        }
    ]
}
```

---

## STEP 10 — agents/runner.py

Create `backend/agents/runner.py`:

```python
"""
CreditBridge Agent Runner
Handles communication between FastAPI and the Neuro SAN agent network.

Two modes:
  USE_AGENTS=true  → runs real Neuro SAN pipeline
  USE_AGENTS=false → runs synthetic fallback (always works, good for demo)

The synthetic fallback is kept permanently as a safety net.
If the agent pipeline fails for any reason, it falls back automatically.
"""
import os
import sys
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Add parent directory to path so coded tools can import from data/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import USE_AGENTS, AGENT_MANIFEST_FILE, AGENT_TOOL_PATH, MISTRAL_API_KEY
from data.synthetic_generator import (
    generate_applicant_data,
    score_phone_bill,
    score_ecommerce,
    score_geolocation,
    score_merchant,
    score_cashflow,
    score_psychometric,
    calculate_final_score,
)
from database import get_agent_weights


def run_synthetic_pipeline(
    applicant_id: str,
    consented_sources: list[str],
    questionnaire_answers: list[int],
) -> dict:
    """
    Synthetic scoring pipeline — always works, deterministic.
    Used when USE_AGENTS=false or as fallback if agent pipeline fails.
    """
    weights = get_agent_weights()
    data = generate_applicant_data(applicant_id)

    agent_scores = {}

    if "phone_bill" in consented_sources:
        score, reason = score_phone_bill(data["phone_bill"])
        agent_scores["phone_bill"] = (score, reason)

    if "ecommerce" in consented_sources:
        score, reason = score_ecommerce(data["ecommerce"])
        agent_scores["ecommerce"] = (score, reason)

    if "geolocation" in consented_sources:
        score, reason = score_geolocation(data["geolocation"])
        agent_scores["geolocation"] = (score, reason)

    # Psychometric always runs (questionnaire, not a data API)
    score, reason = score_psychometric(questionnaire_answers)
    agent_scores["psychometric"] = (score, reason)

    if "merchant" in consented_sources:
        score, reason = score_merchant(data["merchant"])
        agent_scores["merchant"] = (score, reason)

    if "cashflow" in consented_sources:
        score, reason = score_cashflow(data["cashflow"])
        agent_scores["cashflow"] = (score, reason)

    # Ensure psychometric weight is always active
    all_active = list(agent_scores.keys())
    active_weights = {k: v for k, v in weights.items() if k in all_active}

    result = calculate_final_score(agent_scores, active_weights, all_active)
    result["pipeline_mode"] = "synthetic"
    result["applicant_id"] = applicant_id
    return result


async def run_agent_pipeline(
    applicant_id: str,
    consented_sources: list[str],
    questionnaire_answers: list[int],
) -> dict:
    """
    Neuro SAN agent pipeline.
    Starts the agent server, calls credit_coordinator, returns result.
    Falls back to synthetic if anything fails.
    """
    if not USE_AGENTS:
        logger.info("USE_AGENTS=false, using synthetic pipeline")
        return run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)

    if not MISTRAL_API_KEY:
        logger.warning("No MISTRAL_API_KEY set, falling back to synthetic pipeline")
        return run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)

    try:
        # Set environment variables for Neuro SAN
        os.environ["MISTRAL_API_KEY"] = MISTRAL_API_KEY
        os.environ["AGENT_MANIFEST_FILE"] = AGENT_MANIFEST_FILE
        os.environ["AGENT_TOOL_PATH"] = AGENT_TOOL_PATH

        # Import Neuro SAN client
        from neuro_san.client.agent_session import AgentSession

        session = AgentSession(
            agent_name="creditbridge",
            connection_type="direct",
        )

        # Build the prompt for the coordinator
        prompt = json.dumps({
            "applicant_id": applicant_id,
            "consented_sources": consented_sources,
            "questionnaire_answers": questionnaire_answers,
        })

        response = session.chat(prompt)

        # Parse response
        if isinstance(response, str):
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("Could not extract JSON from agent response")
        elif isinstance(response, dict):
            result = response
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")

        result["pipeline_mode"] = "neuro_san"
        result["applicant_id"] = applicant_id
        logger.info(f"Agent pipeline completed for {applicant_id}, score={result.get('final_score')}")
        return result

    except Exception as e:
        logger.error(f"Agent pipeline failed: {e}. Falling back to synthetic.")
        result = run_synthetic_pipeline(applicant_id, consented_sources, questionnaire_answers)
        result["pipeline_mode"] = "synthetic_fallback"
        result["fallback_reason"] = str(e)
        return result
```

---

## STEP 11 — FastAPI Routes

### File 11A: routes/applicant.py

```python
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
```

### File 11B: routes/scoring.py

```python
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
```

### File 11C: routes/reports.py

```python
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
```

### File 11D: routes/admin.py

```python
"""
Admin panel routes — weight configuration and analytics.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from database import get_db, log_audit
from auth import verify_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


class WeightUpdateRequest(BaseModel):
    weights: dict[str, float]


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
```

---

## STEP 12 — main.py

Create `backend/main.py`:

```python
"""
CreditBridge FastAPI Application
Entry point for the backend server.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes.applicant import router as applicant_router
from routes.scoring import router as scoring_router
from routes.reports import router as reports_router
from routes.admin import router as admin_router
from config import DEBUG

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CreditBridge API",
    description="AI-powered alternate credit scoring for borrowers with no credit history",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow React frontend on localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(applicant_router)
app.include_router(scoring_router)
app.include_router(reports_router)
app.include_router(admin_router)


@app.on_event("startup")
def startup():
    """Initialize database on server start."""
    logger.info("CreditBridge API starting up...")
    init_db()
    logger.info("Database initialized")


@app.get("/")
def root():
    return {
        "name": "CreditBridge API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "creditbridge-backend"}
```

---

## STEP 13 — demo_seed.py

Create `backend/demo_seed.py`:

```python
"""
CreditBridge Demo Seed Script
Creates 5 pre-built applicants with known scores for demo purposes.
Run ONCE before the demo: python demo_seed.py
"""
import json
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_db, new_id, log_audit
from auth import encrypt_field, hash_aadhaar
from agents.runner import run_synthetic_pipeline

DEMO_APPLICANTS = [
    {
        "id": "demo-ravi-001",
        "name": "Ravi Kumar",
        "phone": "9876500001",
        "email": "ravi.kumar@example.com",
        "aadhaar_last4": "1234",
        "consents": ["phone_bill", "geolocation", "merchant"],
        "answers": [0, 1, 0, 2, 0, 0, 1, 0, 0, 0],  # Good financial behavior
        "profile": "Street vendor, tea stall, Guwahati. Strong phone bill history. No bank account.",
    },
    {
        "id": "demo-priya-002",
        "name": "Priya Sharma",
        "phone": "9876500002",
        "email": "priya.sharma@example.com",
        "aadhaar_last4": "5678",
        "consents": ["phone_bill", "ecommerce", "geolocation", "merchant", "cashflow"],
        "answers": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Excellent financial behavior
        "profile": "MSME owner, textile shop. All data sources, regular income.",
    },
    {
        "id": "demo-ishaq-003",
        "name": "Mohammed Ishaq",
        "phone": "9876500003",
        "email": "m.ishaq@example.com",
        "aadhaar_last4": "9012",
        "consents": ["phone_bill", "geolocation"],
        "answers": [2, 2, 1, 3, 1, 2, 3, 1, 2, 2],  # Lower behavior scores
        "profile": "Agricultural worker, rural area. Limited digital footprint.",
    },
    {
        "id": "demo-sunita-004",
        "name": "Sunita Devi",
        "phone": "9876500004",
        "email": "sunita.devi@example.com",
        "aadhaar_last4": "3456",
        "consents": ["phone_bill", "geolocation", "cashflow"],
        "answers": [0, 1, 0, 1, 0, 1, 1, 0, 0, 0],  # Good behavior, SHG member
        "profile": "SHG member. Jan Dhan account. Consistent phone bills.",
    },
    {
        "id": "demo-arjun-005",
        "name": "Arjun Patel",
        "phone": "9876500005",
        "email": "arjun.patel@example.com",
        "aadhaar_last4": "7890",
        "consents": ["phone_bill", "ecommerce", "geolocation", "cashflow"],
        "answers": [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],  # Very good behavior
        "profile": "Young entrepreneur. High ecommerce activity. Savings account.",
    },
]


def seed():
    print("CreditBridge Demo Seed — Starting...")
    init_db()

    with get_db() as conn:
        # Clear existing demo data
        for app in DEMO_APPLICANTS:
            conn.execute("DELETE FROM credit_scores WHERE applicant_id = ?", (app["id"],))
            conn.execute("DELETE FROM consent_logs WHERE applicant_id = ?", (app["id"],))
            conn.execute("DELETE FROM questionnaire_responses WHERE applicant_id = ?", (app["id"],))
            conn.execute("DELETE FROM audit_log WHERE applicant_id = ?", (app["id"],))
            conn.execute("DELETE FROM applicants WHERE id = ?", (app["id"],))
        conn.commit()

    for app in DEMO_APPLICANTS:
        print(f"  Seeding: {app['name']} ({app['profile'][:50]}...)")

        # Insert applicant
        with get_db() as conn:
            conn.execute(
                """INSERT INTO applicants
                   (id, name, phone_encrypted, email_encrypted, aadhaar_hash)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    app["id"],
                    app["name"],
                    encrypt_field(app["phone"]),
                    encrypt_field(app["email"]),
                    hash_aadhaar(app["aadhaar_last4"]),
                )
            )
            # Insert consents
            from datetime import datetime
            for source in ["phone_bill", "ecommerce", "geolocation", "merchant", "cashflow"]:
                conn.execute(
                    """INSERT INTO consent_logs (id, applicant_id, source_name, consented)
                       VALUES (?, ?, ?, ?)""",
                    (new_id(), app["id"], source, 1 if source in app["consents"] else 0)
                )
            # Insert questionnaire
            conn.execute(
                """INSERT INTO questionnaire_responses (id, applicant_id, answers)
                   VALUES (?, ?, ?)""",
                (new_id(), app["id"], json.dumps(app["answers"]))
            )
            conn.commit()

        # Run synthetic scoring
        result = run_synthetic_pipeline(
            applicant_id=app["id"],
            consented_sources=app["consents"] + ["psychometric"],
            questionnaire_answers=app["answers"],
        )

        # Save score
        breakdown = result.get("breakdown", {})
        with get_db() as conn:
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
                    new_id(), app["id"],
                    breakdown.get("phone_bill",   {}).get("score", 0),
                    breakdown.get("ecommerce",    {}).get("score", 0),
                    breakdown.get("geolocation",  {}).get("score", 0),
                    breakdown.get("psychometric", {}).get("score", 0),
                    breakdown.get("merchant",     {}).get("score", 0),
                    breakdown.get("cashflow",     {}).get("score", 0),
                    result["final_score"],
                    result["risk_category"],
                    result["loan_recommended"],
                    result["interest_rate"],
                    result["explanation"],
                    breakdown.get("phone_bill",   {}).get("reason", ""),
                    breakdown.get("ecommerce",    {}).get("reason", ""),
                    breakdown.get("geolocation",  {}).get("reason", ""),
                    breakdown.get("psychometric", {}).get("reason", ""),
                    breakdown.get("merchant",     {}).get("reason", ""),
                    breakdown.get("cashflow",     {}).get("reason", ""),
                    json.dumps(result.get("weights_used", {})),
                    "synthetic",
                )
            )
            conn.commit()

        print(f"    ✓ Score: {result['final_score']} — {result['risk_category']}")

    print("\nDemo seed complete. 5 applicants loaded.")
    print("Start server: uvicorn main:app --reload --port 8000")
    print("Then open: http://localhost:8000/docs to verify")


if __name__ == "__main__":
    seed()
```

---

## STEP 14 — Frontend Minimal Stub (Ankur expands this)

Create `frontend/` with Vite + React:

```bash
cd creditbridge
npm create vite@latest frontend -- --template react
cd frontend
npm install axios react-router-dom recharts
```

Create `frontend/src/api/client.js`:

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

// Auto-attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cb_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const registerApplicant = (data) => api.post('/api/register', data);
export const login = (username, password) => api.post('/api/auth/login', { username, password });
export const saveConsent = (data) => api.post('/api/consent', data);
export const saveQuestionnaire = (applicant_id, answers) =>
  api.post('/api/questionnaire', { applicant_id, answers });
export const scoreApplicant = (applicant_id, answers) =>
  api.post('/api/score', { applicant_id, questionnaire_answers: answers });
export const getReport = (applicant_id) => api.get(`/api/report/${applicant_id}`);
export const getAllApplicants = () => api.get('/api/applicants');
export const getWeights = () => api.get('/api/admin/weights');
export const updateWeights = (weights) => api.put('/api/admin/weights', { weights });
export const getAnalytics = () => api.get('/api/admin/analytics');

export default api;
```

---

## STEP 15 — HOW TO RUN

After all files are created:

```bash
# Terminal 1 — Backend
cd creditbridge/backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

# Create .env from example and add your Mistral key
cp .env.example .env
# Edit .env: MISTRAL_API_KEY=your_key_here

# Seed demo data
python demo_seed.py

# Start server
uvicorn main:app --reload --port 8000
```

```bash
# Terminal 2 — Frontend (Ankur)
cd creditbridge/frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

```bash
# Verify API is working
# Open browser: http://localhost:8000/docs
# Try POST /api/register with test data
# Try POST /api/score — should return a credit score
```

---

## STEP 16 — TEST CHECKLIST

After setup, verify these work before the demo:

```
[ ] GET  http://localhost:8000/health           → {"status":"healthy"}
[ ] GET  http://localhost:8000/docs             → Swagger UI loads
[ ] POST http://localhost:8000/api/auth/login   → returns JWT token
[ ] POST http://localhost:8000/api/register     → returns applicant_id
[ ] POST http://localhost:8000/api/consent      → returns consent recorded
[ ] POST http://localhost:8000/api/questionnaire → returns submitted
[ ] POST http://localhost:8000/api/score        → returns credit score 300-850
[ ] GET  http://localhost:8000/api/report/{id}  → returns full report
[ ] GET  http://localhost:8000/api/applicants   → returns 5 seeded applicants
[ ] GET  http://localhost:8000/api/admin/analytics → returns stats
[ ] GET  http://localhost:8000/api/admin/weights   → returns agent weights
[ ] GET  http://localhost:8000/api/audit/{id}   → returns audit trail
```

---

## PHASE 2 EXPANSION POINTS (July 4 Final)

These are marked with TODO comments throughout the code.
Expand these after the progress review:

```
TODO 1: Replace synthetic_generator with real telecom API connector
TODO 2: Add real-time ecommerce data via consent OAuth flow
TODO 3: Add Neuro SAN server mode (currently using direct session)
TODO 4: Add PDF report generation (pdfkit or reportlab)
TODO 5: Add Hindi language support in score_explainer agent
TODO 6: Add re-scoring when applicant revokes/adds a consent source
TODO 7: Add JWT refresh token rotation
TODO 8: Add rate limiting on scoring endpoint
TODO 9: Add email notification when score is ready
TODO 10: Add Docker Compose for one-command startup
```

---

*CreditBridge Backend v1.0 — PSB Hackathon 2026*
*UCO Bank × Department of Financial Services × Ministry of Finance*
*Built with Neuro SAN + FastAPI + SQLite*