"""
Helper script to seed MongoDB Atlas with demo merchant filings and trade references.
Leaves data populated so it can be viewed directly in MongoDB collections.
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
logger = logging.getLogger("seed_merchant_demo")

from database_mongo import init_mongo, get_mongo_db, create_gstn_filing, create_merchant_reference


async def seed():
    ok = await init_mongo()
    if not ok:
        logger.error("Failed to connect to MongoDB Atlas.")
        return

    db = get_mongo_db()

    # 1. Seed Karan with GSTN Portal data (Track A)
    await db.gstn_filings.delete_many({"applicant_id": "karan"})
    
    months = ["2024-05", "2024-04", "2024-03", "2024-02", "2024-01", "2023-12", "2023-11", "2023-10", "2023-09", "2023-08", "2023-07", "2023-06"]
    filing_history = []
    # 11/12 returns on time (91%)
    for idx, m in enumerate(months):
        filed_on_time = (idx != 5)  # Late only in December
        filing_history.append({"month": m, "filed_on_time": filed_on_time})

    invoices = [
        {"recipient_gstin": "27KARA1234A1Z1", "amount": 35000.0, "date": "2024-05-02"},
        {"recipient_gstin": "27KARA1234A1Z1", "amount": 30000.0, "date": "2024-05-15"},
        {"recipient_gstin": "27MARK2345B1Z2", "amount": 62000.0, "date": "2024-05-20"},
        {"recipient_gstin": "27DIST3456C1Z3", "amount": 25000.0, "date": "2024-04-10"},
        {"recipient_gstin": "27DIST3456C1Z3", "amount": 28000.0, "date": "2024-04-25"},
        {"recipient_gstin": "27RETA4567D1Z4", "amount": 95000.0, "date": "2024-04-30"},
        {"recipient_gstin": "27SUPER5678E1Z5", "amount": 12000.0, "date": "2024-03-05"},
    ]

    doc_karan = {
        "applicant_id": "karan",
        "gstin": "27KARANGROC1234",
        "business_name": "Karan Grocery and Kirana Store",
        "phone_number": "9876543210",
        "filing_history": filing_history,
        "invoices": invoices,
        "stage": "scored",
        "verification_level": "account_aggregator",
        "upload_timestamp": datetime.now(timezone.utc)
    }
    gst_id = await create_gstn_filing(doc_karan)
    logger.info(f"Seeded Karan's GSTN profile in collection `gstn_filings` (ID: {gst_id})")

    # 2. Seed Ravi Kumar with offline verified Trade References (Track B)
    await db.merchant_references.delete_many({"applicant_id": "demo-ravi-001"})

    references = [
        {
            "applicant_id": "demo-ravi-001",
            "reference_name": "Sharma Wholesale Agro",
            "phone": "9812345678",
            "relationship_type": "supplier",
            "duration_months": 48,
            "verified_status": "verified",
            "rating": 4.8,
            "verification_timestamp": datetime.now(timezone.utc)
        },
        {
            "applicant_id": "demo-ravi-001",
            "reference_name": "Gupta Seeds Distributor",
            "phone": "9823456789",
            "relationship_type": "supplier",
            "duration_months": 24,
            "verified_status": "verified",
            "rating": 4.2,
            "verification_timestamp": datetime.now(timezone.utc)
        },
        {
            "applicant_id": "demo-ravi-001",
            "reference_name": "Local Buyer Cafe",
            "phone": "9834567890",
            "relationship_type": "buyer",
            "duration_months": 12,
            "verified_status": "pending",
            "rating": 0.0
        }
    ]

    for ref in references:
        ref_id = await create_merchant_reference(ref)
        # Update references directly with verification timestamps if verified
        if ref["verified_status"] == "verified":
            await db.merchant_references.update_one(
                {"_id": ref_id},
                {"$set": {"verified_status": "verified", "rating": ref["rating"]}}
            )
            
    logger.info(f"Seeded Ravi Kumar's trade references in collection `merchant_references` (3 profiles)")

    logger.info("MongoDB Atlas demo seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
