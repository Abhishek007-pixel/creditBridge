"""
Debug script: query MongoDB for karan's documents and print their stages.
"""
import asyncio
from database_mongo import init_mongo, get_mongo_db

async def main():
    await init_mongo()
    db = get_mongo_db()
    docs = await db.bill_documents.find({"applicant_id": "karan"}).to_list(None)
    print(f"Total documents for karan: {len(docs)}")
    for d in docs:
        print(f"- Filename: {d.get('original_filename')}, Stage: {d.get('stage')}, Score: {d.get('stream_score')}, Type: {d.get('extraction', {}).get('bill_type') if d.get('extraction') else 'None'}")

if __name__ == "__main__":
    asyncio.run(main())
