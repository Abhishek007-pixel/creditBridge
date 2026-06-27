"""
Helper script to seed MongoDB Atlas with demo geolocation coordinates and Aadhaar parsing.
Leaves data populated so it can be viewed directly in MongoDB.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime, timezone

# Add backend root to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_geolocation_demo")

from database_mongo import init_mongo, get_mongo_db, create_aadhaar_address, create_gps_verification


async def seed():
    ok = await init_mongo()
    if not ok:
        logger.error("Failed to connect to MongoDB Atlas.")
        return

    db = get_mongo_db()

    # 1. Seed Karan with Geolocation data
    # Residential Address (Delhi Dwarka - 110001)
    await db.aadhaar_addresses.delete_many({"applicant_id": "karan"})
    await db.gps_verifications.delete_many({"applicant_id": "karan"})

    doc_aadhaar = {
        "applicant_id": "karan",
        "original_filename": "karan_aadhaar_back.pdf",
        "file_hash": "sha256:fakehashaadhaarkaran123",
        "stage": "scored",
        "city": "New Delhi",
        "state": "Delhi",
        "pin_code": "110001",
        "street": "Dwarka Sector 5",
        "upload_timestamp": datetime.now(timezone.utc)
    }
    await create_aadhaar_address(doc_aadhaar)
    logger.info("Seeded Karan's Aadhaar address profile in `aadhaar_addresses` collection.")

    doc_gps = {
        "applicant_id": "karan",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "city": "Delhi",
        "state": "Delhi",
        "pin_code": "110001",
        "timestamp": datetime.now(timezone.utc)
    }
    await create_gps_verification(doc_gps)
    logger.info("Seeded Karan's Live presence coords in `gps_verifications` collection.")

    # Update account_aggregators profile billing address for karan to match 110001
    await db.account_aggregators.update_many(
        {"applicant_id": "karan"},
        {"$set": {
            "billing_pin_code": "110001",
            "billing_city": "Delhi",
            "billing_state": "Delhi"
        }}
    )
    logger.info("Updated Karan's bank billing profiles to match PIN code 110001.")

    logger.info("MongoDB Atlas geolocation seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
