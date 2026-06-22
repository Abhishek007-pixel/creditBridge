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
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
AGENT_MODEL_NAME: str = os.getenv("AGENT_MODEL_NAME", "")
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
