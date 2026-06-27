"""
Quick test: verify MongoDB Atlas connection and basic operations.
Run from backend directory:
  venv\Scripts\python test_mongo.py
"""
import asyncio
from datetime import datetime, timezone

async def main():
    print("=" * 55)
    print("  CreditBridge - MongoDB Atlas Connection Test")
    print("=" * 55)

    from database_mongo import init_mongo, get_mongo_db

    ok = await init_mongo()
    if not ok:
        print("\nFAILED - Could not connect to MongoDB Atlas.")
        print("   Check your MONGODB_URI in .env")
        return

    db = get_mongo_db()

    # 1. Insert test document
    test_doc = {
        "applicant_id": "test-connection-check",
        "test": True,
        "timestamp": datetime.now(timezone.utc),
        "message": "CreditBridge MongoDB connection verified"
    }
    result = await db.connection_tests.insert_one(test_doc)
    print(f"\n[OK] Insert    _id: {result.inserted_id}")

    # 2. Read it back
    found = await db.connection_tests.find_one({"_id": result.inserted_id})
    print(f"[OK] Read      message: {found['message']}")

    # 3. Delete the test doc (cleanup)
    await db.connection_tests.delete_one({"_id": result.inserted_id})
    print(f"[OK] Delete    test doc cleaned up")

    # 4. List all collections
    collections = await db.list_collection_names()
    print(f"\n[DB] Collections in '{db.name}': {collections if collections else '(empty - first run)'}")

    print("\n" + "=" * 55)
    print("  SUCCESS: MongoDB Atlas is ready for CreditBridge!")
    print("=" * 55)

if __name__ == "__main__":
    asyncio.run(main())
