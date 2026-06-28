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

    # ── bank_statements ───────────────────────────────────────────────────
    await db.bank_statements.create_index("applicant_id")
    await db.bank_statements.create_index("file_hash")
    await db.bank_statements.create_index("verification_level")

    # ── account_aggregators ───────────────────────────────────────────────
    await db.account_aggregators.create_index("applicant_id")
    await db.account_aggregators.create_index("phone_number")

    # ── ecommerce_invoices ───────────────────────────────────────────────
    await db.ecommerce_invoices.create_index("applicant_id")
    await db.ecommerce_invoices.create_index("file_hash")
    await db.ecommerce_invoices.create_index("stage")

    # ── financial_commitments ────────────────────────────────────────────
    await db.financial_commitments.create_index("applicant_id")
    await db.financial_commitments.create_index("file_hash")
    await db.financial_commitments.create_index("stage")

    # ── gstn_filings ─────────────────────────────────────────────────────
    await db.gstn_filings.create_index("applicant_id")
    await db.gstn_filings.create_index("file_hash")
    await db.gstn_filings.create_index("stage")

    # ── merchant_references ──────────────────────────────────────────────
    await db.merchant_references.create_index("applicant_id")
    await db.merchant_references.create_index("verified_status")

    # ── aadhaar_addresses ────────────────────────────────────────────────
    await db.aadhaar_addresses.create_index("applicant_id")

    # ── gps_verifications ────────────────────────────────────────────────
    await db.gps_verifications.create_index("applicant_id")

    # ── users ────────────────────────────────────────────────────────────
    await db.users.create_index("email", unique=True)
    await db.users.create_index("uid", unique=True)

    # ── questionnaire_responses ──────────────────────────────────────────
    await db.questionnaire_responses.create_index("applicant_id")

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


# ── bank_statements helpers ────────────────────────────────────────────────

async def create_bank_statement(doc: dict) -> str:
    """Insert a new bank statement record."""
    db = get_mongo_db()
    doc.setdefault("upload_timestamp", datetime.now(timezone.utc))
    doc.setdefault("stage", "uploaded")
    doc.setdefault("flags", [])
    doc.setdefault("transactions", [])
    result = await db.bank_statements.insert_one(doc)
    return str(result.inserted_id)


async def get_bank_statements_for_applicant(applicant_id: str) -> list:
    """Retrieve bank statements for an applicant, excluding raw file bytes."""
    db = get_mongo_db()
    cursor = db.bank_statements.find(
        {"applicant_id": applicant_id},
        {"file_bytes_b64": 0}
    ).sort("upload_timestamp", -1)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs


async def update_bank_statement(doc_id: str, update: dict) -> bool:
    """Update bank statement fields by _id."""
    from bson import ObjectId
    db = get_mongo_db()
    result = await db.bank_statements.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**update, "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count > 0


async def check_bank_statement_duplicate(applicant_id: str, file_hash: str) -> bool:
    """Check if statement duplicate exists."""
    db = get_mongo_db()
    existing = await db.bank_statements.find_one({
        "applicant_id": applicant_id,
        "file_hash": file_hash,
    })
    return existing is not None


# ── account_aggregators helpers ─────────────────────────────────────────────

async def upsert_aa_feed(applicant_id: str, phone_number: str, bank_name: str, transactions: list):
    """Upsert connected account aggregator feed transactions."""
    db = get_mongo_db()
    await db.account_aggregators.update_one(
        {
            "applicant_id": applicant_id,
            "phone_number": phone_number,
            "bank_name": bank_name,
        },
        {
            "$set": {
                "transactions": transactions,
                "verification_level": "account_aggregator",
                "connected_at": datetime.now(timezone.utc),
            }
        },
        upsert=True
    )


async def get_aa_feeds_for_applicant(applicant_id: str) -> list:
    """Retrieve all AA connected feeds for an applicant."""
    db = get_mongo_db()
    cursor = db.account_aggregators.find({"applicant_id": applicant_id})
    feeds = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        feeds.append(doc)
    return feeds


# ── ecommerce_invoices helpers ─────────────────────────────────────────────

async def create_ecommerce_invoice(doc: dict) -> str:
    """Insert a new ecommerce invoice record."""
    db = get_mongo_db()
    doc.setdefault("upload_timestamp", datetime.now(timezone.utc))
    doc.setdefault("stage", "uploaded")
    doc.setdefault("verification_level", "document_uploaded")
    result = await db.ecommerce_invoices.insert_one(doc)
    return str(result.inserted_id)


async def get_ecommerce_invoices_for_applicant(applicant_id: str) -> list:
    """Retrieve ecommerce invoices for an applicant, excluding raw file bytes."""
    db = get_mongo_db()
    cursor = db.ecommerce_invoices.find(
        {"applicant_id": applicant_id},
        {"file_bytes_b64": 0}
    ).sort("upload_timestamp", -1)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs


async def update_ecommerce_invoice(doc_id: str, update: dict) -> bool:
    """Update ecommerce invoice fields by _id."""
    from bson import ObjectId
    db = get_mongo_db()
    result = await db.ecommerce_invoices.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**update, "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count > 0


async def check_ecommerce_invoice_duplicate(applicant_id: str, file_hash: str) -> bool:
    """Check if ecommerce invoice duplicate exists."""
    db = get_mongo_db()
    existing = await db.ecommerce_invoices.find_one({
        "applicant_id": applicant_id,
        "file_hash": file_hash,
    })
    return existing is not None


# ── financial_commitments helpers ────────────────────────────────────────────

async def create_financial_commitment(doc: dict) -> str:
    """Insert a new financial commitment record."""
    db = get_mongo_db()
    doc.setdefault("upload_timestamp", datetime.now(timezone.utc))
    doc.setdefault("stage", "uploaded")
    doc.setdefault("verification_level", "document_uploaded")
    result = await db.financial_commitments.insert_one(doc)
    return str(result.inserted_id)


async def get_financial_commitments_for_applicant(applicant_id: str) -> list:
    """Retrieve financial commitments for an applicant, excluding raw file bytes."""
    db = get_mongo_db()
    cursor = db.financial_commitments.find(
        {"applicant_id": applicant_id},
        {"file_bytes_b64": 0}
    ).sort("upload_timestamp", -1)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs


async def update_financial_commitment(doc_id: str, update: dict) -> bool:
    """Update financial commitment fields by _id."""
    from bson import ObjectId
    db = get_mongo_db()
    result = await db.financial_commitments.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**update, "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count > 0


async def check_financial_commitment_duplicate(applicant_id: str, file_hash: str) -> bool:
    """Check if financial commitment duplicate exists."""
    db = get_mongo_db()
    existing = await db.financial_commitments.find_one({
        "applicant_id": applicant_id,
        "file_hash": file_hash,
    })
    return existing is not None


# ── gstn_filings helpers ───────────────────────────────────────────────────

async def create_gstn_filing(doc: dict) -> str:
    """Insert a new GST filing record."""
    db = get_mongo_db()
    doc.setdefault("upload_timestamp", datetime.now(timezone.utc))
    doc.setdefault("stage", "uploaded")
    result = await db.gstn_filings.insert_one(doc)
    return str(result.inserted_id)


async def get_gstn_filings_for_applicant(applicant_id: str) -> list:
    """Retrieve GST filings for an applicant, excluding raw file bytes."""
    db = get_mongo_db()
    cursor = db.gstn_filings.find(
        {"applicant_id": applicant_id},
        {"file_bytes_b64": 0}
    ).sort("upload_timestamp", -1)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs


async def update_gstn_filing(doc_id: str, update: dict) -> bool:
    """Update GST filing fields by _id."""
    from bson import ObjectId
    db = get_mongo_db()
    result = await db.gstn_filings.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**update, "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count > 0


async def check_gstn_filing_duplicate(applicant_id: str, file_hash: str) -> bool:
    """Check if GST filing duplicate exists."""
    db = get_mongo_db()
    existing = await db.gstn_filings.find_one({
        "applicant_id": applicant_id,
        "file_hash": file_hash,
    })
    return existing is not None


# ── merchant_references helpers ────────────────────────────────────────────

async def create_merchant_reference(doc: dict) -> str:
    """Insert a new merchant reference contact."""
    db = get_mongo_db()
    doc.setdefault("created_at", datetime.now(timezone.utc))
    doc.setdefault("verified_status", "pending")
    doc.setdefault("rating", 0.0)
    result = await db.merchant_references.insert_one(doc)
    return str(result.inserted_id)


async def get_merchant_references_for_applicant(applicant_id: str) -> list:
    """Retrieve all merchant references for an applicant."""
    db = get_mongo_db()
    cursor = db.merchant_references.find({"applicant_id": applicant_id})
    refs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        refs.append(doc)
    return refs


async def update_merchant_reference(doc_id: str, update: dict) -> bool:
    """Update merchant reference contact by _id."""
    from bson import ObjectId
    db = get_mongo_db()
    result = await db.merchant_references.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {**update, "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count > 0


# ── geolocation helpers ────────────────────────────────────────────────────

async def create_aadhaar_address(doc: dict) -> str:
    """Insert a new Aadhaar address parsing record."""
    db = get_mongo_db()
    doc.setdefault("upload_timestamp", datetime.now(timezone.utc))
    doc.setdefault("stage", "scored")
    result = await db.aadhaar_addresses.insert_one(doc)
    return str(result.inserted_id)


async def create_gps_verification(doc: dict) -> str:
    """Insert a new Live GPS location capture record."""
    db = get_mongo_db()
    doc.setdefault("timestamp", datetime.now(timezone.utc))
    result = await db.gps_verifications.insert_one(doc)
    return str(result.inserted_id)


# ── users and questionnaire_responses helpers ─────────────────────────────

async def get_user_from_mongo(email_or_username: str) -> Optional[dict]:
    """Retrieve user details from MongoDB by email or username."""
    if not is_mongo_available():
        return None
    db = get_mongo_db()
    # Accept either username or email
    user = await db.users.find_one({
        "$or": [
            {"email": email_or_username},
            {"username": email_or_username}
        ]
    })
    if user:
        user["_id"] = str(user["_id"])
    return user


async def create_user_in_mongo(user_doc: dict) -> str:
    """Insert a new user (applicant, officer, admin) record into MongoDB users collection."""
    db = get_mongo_db()
    user_doc.setdefault("created_at", datetime.now(timezone.utc))
    result = await db.users.insert_one(user_doc)
    return str(result.inserted_id)


async def save_questionnaire_response_mongo(applicant_id: str, answers: list) -> str:
    """Save questionnaire responses in MongoDB Atlas."""
    db = get_mongo_db()
    doc = {
        "applicant_id": applicant_id,
        "answers": answers,
        "submitted_at": datetime.now(timezone.utc)
    }
    result = await db.questionnaire_responses.insert_one(doc)
    return str(result.inserted_id)





