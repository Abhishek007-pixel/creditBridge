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
