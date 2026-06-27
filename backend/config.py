"""
CreditBridge Configuration
Supports Gemini, Mistral, and OpenAI providers dynamically.
Set exactly ONE API key in .env — the system detects which one.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider keys ────────────────────────────────────────────────────
GEMINI_API_KEY: str  = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
OPENAI_API_KEY: str  = os.getenv("OPENAI_API_KEY", "")


def get_active_api_key() -> tuple:
    """Returns (env_var_name, api_key_value) for whichever key is set."""
    if GEMINI_API_KEY and GEMINI_API_KEY not in ("your_gemini_api_key_here", ""):
        return "GOOGLE_API_KEY", GEMINI_API_KEY
    if MISTRAL_API_KEY and MISTRAL_API_KEY not in ("your_mistral_api_key_here", ""):
        return "MISTRAL_API_KEY", MISTRAL_API_KEY
    if OPENAI_API_KEY and OPENAI_API_KEY not in ("your_openai_api_key_here", ""):
        return "OPENAI_API_KEY", OPENAI_API_KEY
    return "", ""


AGENT_MODEL_NAME: str = os.getenv(
    "AGENT_MODEL_NAME", "gemini/gemini-2.0-flash"
)

# ── Backend config ───────────────────────────────────────────────────────
SECRET_KEY: str   = os.getenv("SECRET_KEY", "dev-secret-key-min-32-chars-change-in-prod")
DATABASE_URL: str = os.getenv("DATABASE_URL", "./creditbridge.db")
DEBUG: bool       = os.getenv("DEBUG", "true").lower() == "true"

# ── Neuro SAN config ─────────────────────────────────────────────────────
# For ns run (studio):   registries/manifest.hocon  (root level)
# For direct session:    agents/registries/manifest.hocon
AGENT_MANIFEST_FILE: str = os.getenv(
    "AGENT_MANIFEST_FILE", "registries/manifest.hocon"
)
AGENT_TOOL_PATH: str = os.getenv("AGENT_TOOL_PATH", ".")
USE_AGENTS: bool     = os.getenv("USE_AGENTS", "true").lower() == "true"

# ── JWT config ───────────────────────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_HOURS: int = 24
ALGORITHM: str = "HS256"

# ── Default agent weights ────────────────────────────────────────────────
DEFAULT_WEIGHTS: dict = {
    "phone_bill":    0.25,
    "cashflow":      0.20,
    "psychometric":  0.20,
    "geolocation":   0.15,
    "ecommerce":     0.12,
    "merchant":      0.08,
}

# ── Score bands ──────────────────────────────────────────────────────────
# (min, max, label, max_loan_inr, interest_rate_pct)
SCORE_BANDS = {
    "low":         (750, 850, "Low Risk — Pre-approved",             500000, 10.5),
    "low_medium":  (650, 749, "Low-Medium Risk — Approved",          300000, 12.0),
    "medium":      (550, 649, "Medium Risk — Conditional Approval",  100000, 15.0),
    "medium_high": (450, 549, "Medium-High Risk — Careful Review",    50000, 18.0),
    "high":        (300, 449, "High Risk — Not Recommended",              0,  0.0),
}

# ── Demo users (hardcoded for hackathon) ─────────────────────────────────
DEMO_USERS = {
    # Username-based (old frontend)
    "applicant":   {"password": "password123", "role": "applicant"},
    "bankofficer": {"password": "bankpass123",  "role": "officer"},
    "admin":       {"password": "admin123",     "role": "admin"},
    # Email-based (frontend2 quick-login buttons)
    "priya@creditbridge.com":   {"password": "password123", "role": "applicant", "name": "Priya Sharma",     "uid": "demo-priya-002"},
    "ravi@creditbridge.com":    {"password": "password123", "role": "applicant", "name": "Ravi Kumar",       "uid": "demo-ravi-001"},
    "officer@creditbridge.com": {"password": "bankpass123",  "role": "officer",   "name": "UCO Bank Officer", "uid": "demo-officer-001"},
    "admin@creditbridge.com":   {"password": "admin123",     "role": "admin",     "name": "Global Admin",    "uid": "demo-admin-001"},
}
