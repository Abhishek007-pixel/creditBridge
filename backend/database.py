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
