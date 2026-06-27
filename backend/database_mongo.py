"""
CreditBridge — MongoDB Atlas Layer
Uses Motor (async pymongo) for non-blocking DB access in FastAPI.

Collections managed here:
  bill_documents   — uploaded files + OCR + LLM extraction + score per bill
  bill_streams     — aggregated consistency analysis per bill_type+payee
  applicants_mongo — (future) full applicant profiles when migrating from SQLite
  audit_logs_mongo — (future) audit trail when migrating from SQLite

Existing SQLite tables (applicants, credit_scores, consent_logs, etc.)
are still handled by database.py — this file adds MongoDB on top for
Bill Agent data without touching the working SQLite layer.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URI: str = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://finance_user:Abhi123@cluster0.m3cq5qa.mongodb.net/creditbridge?appName=Cluster0"
)
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "creditbridge")

# ── Singleton client (created once on startup) ─────────────────────────────
_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db: Optional[AsyncIOMotorDatabase] = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Return the singleton Motor client. Call init_mongo() first."""
    if _mongo_client is None:
        raise RuntimeError("MongoDB not initialized. Call init_mongo() first.")
    return _mongo_client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the creditbridge database handle."""
    if _mongo_db is None:
        raise RuntimeError("MongoDB not initialized. Call init_mongo() first.")
    return _mongo_db


async def init_mongo() -> bool:
    """
    Initialize MongoDB connection and create indexes.
    Called from FastAPI startup event.
    Returns True on success, False on failure (so app still starts on error).
    """
    global _mongo_client, _mongo_db
    try:
        logger.info(f"Connecting to MongoDB Atlas: {MONGODB_URI[:50]}...")
        _mongo_client = AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
        )
        _mongo_db = _mongo_client[MONGODB_DB_NAME]

        # Verify connection with a ping
        await _mongo_client.admin.command("ping")
        logger.info(f"✅ MongoDB Atlas connected — database: '{MONGODB_DB_NAME}'")

        # Create indexes
        await _create_indexes()
        return True

    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        logger.warning("App will continue without MongoDB (Bill Agent features unavailable).")
        _mongo_client = None
        _mongo_db = None
        return False


async def close_mongo():
    """Close MongoDB connection on app shutdown."""
    global _mongo_client, _mongo_db
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        logger.info("MongoDB connection closed.")


async def _create_indexes():
    """Create indexes for all collections. Safe to call multiple times."""
    db = _mongo_db

    # ── bill_documents ────────────────────────────────────────────────────
    await db.bill_documents.create_index("applicant_id")
    await db.bill_documents.create_index("file_hash")          # dedup check
    await db.bill_documents.create_index("upload_timestamp")
    await db.bill_documents.create_index("stage")              # filter by processing stage
    await db.bill_documents.create_index(
        [("applicant_id", 1), ("stage", 1)]
    )

    # ── bill_streams ──────────────────────────────────────────────────────
    await db.bill_streams.create_index("applicant_id")
    await db.bill_streams.create_index(
        [("applicant_id", 1), ("bill_type", 1), ("payee_name", 1)],
        unique=True,
        name="unique_stream_per_applicant"
    )

    # ── applicants_mongo (for future full migration) ──────────────────────
    await db.applicants_mongo.create_index("email", sparse=True)
    await db.applicants_mongo.create_index("sqlite_id", sparse=True)  # bridge to SQLite id

    logger.info("MongoDB indexes created/verified.")


# ── Helper: is MongoDB available? ─────────────────────────────────────────

def is_mongo_available() -> bool:
    """Check if MongoDB is connected. Use this before calling Mongo operations."""
    return _mongo_db is not None


# ── bill_documents helpers ─────────────────────────────────────────────────

async def create_bill_document(doc: dict) -> str:
    """
    Insert a new bill document record.
    Returns the inserted _id as string.

    Expected doc shape:
    {
        applicant_id: str,
        original_filename: str,
        file_hash: str,           # sha256 of file bytes
        file_bytes_b64: str,      # base64-encoded file (for GridFS-lite storage)
        mime_type: str,
        file_size_bytes: int,
        stage: "uploaded",        # uploaded | extracting | classified | scored | rejected
        upload_timestamp: datetime,
        classification: None,
        extraction: None,
        verification_level: "document_uploaded",
        flags: [],
        stream_score: None,
        reason: None,
    }
    """
    db = get_mongo_db()
    doc.setdefault("upload_timestamp", datetime.now(timezone.utc))
    doc.setdefault("stage", "uploaded")
    doc.setdefault("flags", [])
    doc.setdefault("classification", None)
    doc.setdefault("extraction", None)
    doc.setdefault("stream_score", None)
    doc.setdefault("reason", None)

    result = await db.bill_documents.insert_one(doc)
    return str(result.inserted_id)


async def get_bill_documents_for_applicant(applicant_id: str) -> list:
    """Return all bill documents for an applicant (excluding raw file bytes)."""
    db = get_mongo_db()
    cursor = db.bill_documents.find(
        {"applicant_id": applicant_id},
        {"file_bytes_b64": 0}   # exclude heavy field from list view
    ).sort("upload_timestamp", -1)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs


async def update_bill_document(doc_id: str, update: dict) -> bool:
    """Update fields on a bill document by its string _id."""
    from bson import ObjectId
    db = get_mongo_db()
    result = await db.bill_documents.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**update, "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count > 0


async def check_file_duplicate(applicant_id: str, file_hash: str) -> bool:
    """
    Return True if this file hash already exists for this applicant.
    Used to reject duplicate uploads.
    """
    db = get_mongo_db()
    existing = await db.bill_documents.find_one({
        "applicant_id": applicant_id,
        "file_hash": file_hash,
    })
    return existing is not None


# ── bill_streams helpers ───────────────────────────────────────────────────

async def upsert_bill_stream(applicant_id: str, bill_type: str, payee_name: str, stream_data: dict):
    """
    Insert or update a bill stream (aggregated consistency for one payee+type combo).
    Uses upsert so re-scoring just updates the existing record.
    """
    db = get_mongo_db()
    await db.bill_streams.update_one(
        {
            "applicant_id": applicant_id,
            "bill_type": bill_type,
            "payee_name": payee_name,
        },
        {
            "$set": {
                **stream_data,
                "applicant_id": applicant_id,
                "bill_type": bill_type,
                "payee_name": payee_name,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


async def get_bill_streams_for_applicant(applicant_id: str) -> list:
    """Return all bill streams for an applicant (for scoring + display)."""
    db = get_mongo_db()
    cursor = db.bill_streams.find({"applicant_id": applicant_id})
    streams = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        streams.append(doc)
    return streams
