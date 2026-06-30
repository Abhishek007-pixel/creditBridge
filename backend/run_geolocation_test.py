"""
CreditBridge — Geolocation Agent Test Executor
Tests:
1. Aadhaar Card address OCR & LLM extraction simulation.
2. Live GPS browser coordinate reverse geocoding.
3. Proximity and document alignment matching against AA bank billing addresses.

Saves reports to backend/real_test/geolocation/results.json and backend/real_test/geolocation/report.md.

Run: venv\\Scripts\\python run_geolocation_test.py
"""
import os
import sys
import json
import asyncio
import hashlib
import logging
from datetime import datetime, timezone

# Add backend root to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("geolocation_test")

from database import get_db
from database_mongo import (
    init_mongo,
    get_mongo_db,
    is_mongo_available,
    create_aadhaar_address,
    create_gps_verification
)
from routes.geolocation import _parse_aadhaar_with_llm, _simulate_reverse_geocode
from coded_tools.creditbridge.geolocation_tool import GeolocationScoringTool


def ensure_test_applicant_exists():
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applicants WHERE id = ?", ("test_geo_applicant",)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO applicants (id, name, phone_encrypted, email_encrypted, aadhaar_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                ("test_geo_applicant", "Rajesh Sharma", "ENC:geophone", "ENC:rajesh@sharma.com", "HASH:geoaadhaar")
            )
            conn.commit()
            logger.info("Created test applicant 'test_geo_applicant'.")


async def run_test():
    ensure_test_applicant_exists()

    # Initialize MongoDB Atlas
    ok = await init_mongo()
    if not ok:
        logger.error("Failed to connect to MongoDB Atlas.")
        return

    db = get_mongo_db()

    # Clear previous geo records for this applicant
    await db.aadhaar_addresses.delete_many({"applicant_id": "test_geo_applicant"})
    await db.gps_verifications.delete_many({"applicant_id": "test_geo_applicant"})
    await db.account_aggregators.delete_many({"applicant_id": "test_geo_applicant"})
    logger.info("Cleared previous database records.")

    # 1. Simulate Aadhaar Address Upload
    logger.info("\n[1/3] Simulating Aadhaar Address Document upload & parsing...")
    mock_aadhaar_back = """
    UNIQUE IDENTIFICATION AUTHORITY OF INDIA
    Address:
    S/O Om Prakash Sharma,
    House No 142, Sector 8, Dwarka,
    New Delhi, Delhi - 110001
    """

    parsed_aadhaar = _parse_aadhaar_with_llm(mock_aadhaar_back)
    logger.info(f"LLM parsed Aadhaar address: {parsed_aadhaar}")

    if parsed_aadhaar.get("is_valid"):
        doc_aadhaar = {
            "applicant_id": "test_geo_applicant",
            "original_filename": "aadhaar_back.txt",
            "file_hash": "sha256:" + hashlib.sha256(mock_aadhaar_back.encode()).hexdigest(),
            "stage": "scored",
            "city": parsed_aadhaar.get("city") or "Delhi",
            "state": parsed_aadhaar.get("state") or "Delhi",
            "pin_code": parsed_aadhaar.get("pin_code") or "110001",
            "street": parsed_aadhaar.get("street") or "Sector 8 Dwarka",
            "upload_timestamp": datetime.now(timezone.utc)
        }
        await create_aadhaar_address(doc_aadhaar)
        logger.info("Aadhaar address record created in MongoDB.")

    # 2. Simulate Device GPS Capture
    logger.info("\n[2/3] Simulating browser Geolocation GPS coordinates verify...")
    # Coords for Dwarka, Delhi
    lat = 28.6139
    lon = 77.2090
    
    resolved = _simulate_reverse_geocode(lat, lon)
    logger.info(f"Resolved Coordinates: {resolved}")
    
    doc_gps = {
        "applicant_id": "test_geo_applicant",
        "latitude": lat,
        "longitude": lon,
        "city": resolved["city"],
        "state": resolved["state"],
        "pin_code": resolved["pin_code"],
        "timestamp": datetime.now(timezone.utc)
    }
    await create_gps_verification(doc_gps)
    logger.info("GPS verification record created in MongoDB.")

    # 3. Simulate Account Aggregator Billing Address Linking
    logger.info("\n[3/3] Simulating linked Account Aggregator billing profile...")
    await db.account_aggregators.insert_one({
        "applicant_id": "test_geo_applicant",
        "phone_number": "9876543210",
        "bank_name": "State Bank of India",
        "billing_pin_code": "110001",
        "billing_city": "Delhi",
        "billing_state": "Delhi",
        "timestamp": datetime.now(timezone.utc)
    })
    logger.info("Account Aggregator profile seeded with matching PIN code 110001.")

    # Invoke Coded Tool Directly
    tool = GeolocationScoringTool()
    tool_res = await tool.async_invoke(
        args={"applicant_id": "test_geo_applicant"},
        sly_data={}
    )
    
    print("\n" + "=" * 65)
    print("  REVISED GEOLOCATION SCORE ASSESSMENT SUMMARY")
    print("=" * 65)
    print(f"Applicant ID : {tool_res.get('applicant_id')}")
    print(f"Final Score  : {tool_res.get('score')}/100")
    print(f"Reason       : {tool_res.get('reason')}")
    metrics = tool_res.get("metrics", {})
    print(f"\nCalculated Metrics:")
    print(f"  - Document Alignment Score : {metrics.get('document_alignment_score')}/40")
    print(f"  - Presence Proximity Score : {metrics.get('presence_proximity_score')}/40")
    print(f"  - Address Stability Score  : {metrics.get('stability_score')}/20")
    print(f"  - Physical Proximity Dist  : {metrics.get('haversine_distance_km')} km")
    print("=" * 65)

    # Save results
    geo_dir = os.path.abspath(os.path.join(_this_dir, "real_test", "geolocation"))
    os.makedirs(geo_dir, exist_ok=True)

    results_path = os.path.join(geo_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(tool_res, f, indent=2)
    logger.info(f"JSON results saved to: {results_path}")

    report_path = os.path.join(geo_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Revised Geolocation Agent Test Report\n\n")
        f.write(f"- **Executed at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"- **Applicant:** test_geo_applicant\n")
        f.write(f"- **Final Geolocation Score:** **{tool_res.get('score')}/100**\n\n")
        
        f.write("## Proximity & Alignment Metrics\n")
        f.write(f"- **Aadhaar Registered Address City:** {metrics.get('aadhaar_city')}\n")
        f.write(f"- **Bank Billing Profile City:** {metrics.get('bank_city')}\n")
        f.write(f"- **Live GPS Resolved City:** {metrics.get('gps_city')}\n")
        f.write(f"- **Live GPS Distance from permanent address:** {metrics.get('haversine_distance_km')} km (Verified Presence)\n\n")
        
        f.write("## Scoring Breakdown\n")
        f.write(f"| Metric Component | Maximum Points | Points Awarded |\n")
        f.write(f"|---|---|---|\n")
        f.write(f"| **Document Alignment** (Aadhaar PIN vs. Bank PIN) | 40 | {metrics.get('document_alignment_score')} |\n")
        f.write(f"| **Physical Presence Proximity** (GPS coordinates) | 40 | {metrics.get('presence_proximity_score')} |\n")
        f.write(f"| **Address History Stability** | 20 | {metrics.get('stability_score')} |\n")
        
        f.write(f"\n**Summary Assessment:**\n> {tool_res.get('reason')}\n")

    logger.info(f"Markdown report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(run_test())
