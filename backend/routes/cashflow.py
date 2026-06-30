"""
Cashflow Routing Layer — /api/cashflow/*
Handles bank statement PDF/CSV uploads, OCR transaction parsing,
and RBI Account Aggregator (AA) simulator consents.
"""
import io
import json
import base64
import hashlib
import logging
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Header
from pydantic import BaseModel

from database_mongo import (
    is_mongo_available,
    get_mongo_db,
    create_bank_statement,
    get_bank_statements_for_applicant,
    update_bank_statement,
    check_bank_statement_duplicate,
    upsert_aa_feed,
    get_aa_feeds_for_applicant,
)
from database import get_db, log_audit
from data.cashflow_seeds import get_transactions_by_phone
from config import MISTRAL_API_KEY
from utils.ocr import call_mistral_text, extract_document_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cashflow", tags=["cashflow"])

MISTRAL_TEXT_MODEL = "mistral-medium-latest"
MISTRAL_OCR_MODEL = "mistral-ocr-latest"
MISTRAL_API_BASE = "https://api.mistral.ai/v1"

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls", ".txt", ".jpg", ".png", ".jpeg"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


# ── Pydantic Request Models ──────────────────────────────────────────────────

class AASimulateRequest(BaseModel):
    applicant_id: str
    phone_number: str
    bank_name: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _call_mistral_text(prompt: str, max_tokens: int = 800) -> str:
    return call_mistral_text(prompt, max_tokens)


def _parse_transactions_with_llm(raw_text: str) -> list:
    """
    Use LLM to extract transaction entries from unstructured OCR text.
    Returns: list of {date, amount, type, description, is_recurring}
    """
    prompt = f"""You are structured financial transaction extraction tool.
Analyze this bank statement or ledger text, identify up to 15 transaction rows,
and extract them into JSON arrays.

Text:
---
{raw_text[:2500]}
---

Respond with ONLY valid JSON array containing entries, no narration.
JSON format:
[
  {{
    "date": "YYYY-MM-DD",
    "amount": <positive number>,
    "type": "credit | debit",
    "description": "Short explanation",
    "is_recurring": <true | false>
  }}
]"""

    try:
        resp = _call_mistral_text(prompt)
        match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', resp)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.error(f"LLM transaction extraction failed: {e}")
    return []


# ── Async Pipeline Worker ────────────────────────────────────────────────────

async def _process_cashflow_statement(doc_id: str, file_bytes: bytes, mime_type: str, applicant_id: str, ext: str):
    if not is_mongo_available():
        return

    await update_bank_statement(doc_id, {"stage": "extracting"})

    try:
        # Extract text using shared OCR helper
        raw_text, extract_method = extract_document_text(file_bytes, mime_type, ext)

        if not raw_text or len(raw_text.strip()) < 20:
            await update_bank_statement(doc_id, {
                "stage": "rejected",
                "rejection_reason": "Failed to extract readable text."
            })
            return

        # Stage 3/4: LLM Parse & Classify
        await update_bank_statement(doc_id, {"stage": "parsing_transactions", "extract_method": extract_method})
        transactions = await asyncio.to_thread(_parse_transactions_with_llm, raw_text)

        # Stage 5/6: Final scoring updates
        await update_bank_statement(doc_id, {
            "stage": "scored",
            "transactions": transactions,
            "transaction_count": len(transactions),
        })

        log_audit(applicant_id, "CASHFLOW_STATEMENT_PROCESSED", {
            "doc_id": doc_id,
            "transactions_count": len(transactions),
            "verification_level": "document_uploaded"
        })
        logger.info(f"Bank statement {doc_id} processed successfully — {len(transactions)} txs parsed")

    except Exception as e:
        logger.error(f"Cashflow pipeline error on {doc_id}: {e}")
        await update_bank_statement(doc_id, {
            "stage": "rejected",
            "rejection_reason": f"Unexpected pipeline failure: {str(e)[:100]}"
        })


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_bank_statement(
    background_tasks: BackgroundTasks,
    applicant_id: str = Form(...),
    file: UploadFile = File(...),
    verification_level: str = Form("document_uploaded"),  # document_uploaded | self_reported
):
    """Upload a bank statement PDF/CSV or image ledger. Background parsed."""
    if not is_mongo_available():
        raise HTTPException(status_code=503, detail="MongoDB Atlas connection unavailable.")

    # Validate applicant
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applicants WHERE id = ?", (applicant_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Applicant not found.")

    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")

    file_hash = _sha256(file_bytes)
    is_dup = await check_bank_statement_duplicate(applicant_id, file_hash)
    if is_dup:
        raise HTTPException(status_code=409, detail="Duplicate statement file already uploaded.")

    # Save initial record to MongoDB
    file_b64 = base64.b64encode(file_bytes).decode()
    mime_type = file.content_type or "application/octet-stream"

    doc_id = await create_bank_statement({
        "applicant_id": applicant_id,
        "original_filename": filename,
        "file_hash": file_hash,
        "file_bytes_b64": file_b64,
        "mime_type": mime_type,
        "file_size_bytes": len(file_bytes),
        "stage": "uploaded",
        "verification_level": verification_level,
        "transactions": [],
    })

    log_audit(applicant_id, "CASHFLOW_STATEMENT_UPLOADED", {
        "doc_id": doc_id,
        "filename": filename,
        "verification_level": verification_level
    })

    # Start parsing pipeline
    background_tasks.add_task(
        _process_cashflow_statement, doc_id, file_bytes, mime_type, applicant_id, ext
    )

    return {
        "message": "Bank statement uploaded. Processing in background.",
        "doc_id": doc_id,
        "stage": "uploaded",
    }


@router.post("/simulate-aa")
async def simulate_account_aggregator(req: AASimulateRequest):
    """Simulate Account Aggregator digital consent. Seed data linked immediately."""
    if not is_mongo_available():
        raise HTTPException(status_code=503, detail="MongoDB Atlas connection unavailable.")

    # Validate applicant
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applicants WHERE id = ?", (req.applicant_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Applicant not found.")

    # Fetch seed transactions matching the simulated phone number
    transactions = get_transactions_by_phone(req.phone_number)
    
    await upsert_aa_feed(
        applicant_id=req.applicant_id,
        phone_number=req.phone_number,
        bank_name=req.bank_name,
        transactions=transactions
    )

    log_audit(req.applicant_id, "CASHFLOW_AA_CONNECTED", {
        "phone_number": req.phone_number,
        "bank_name": req.bank_name,
        "transactions_count": len(transactions)
    })

    return {
        "message": f"Successfully simulated Account Aggregator flow for {req.bank_name}.",
        "phone_number": req.phone_number,
        "bank_name": req.bank_name,
        "transactions_count": len(transactions),
        "verification_level": "account_aggregator"
    }


@router.get("/{applicant_id}")
async def get_applicant_cashflow_records(applicant_id: str):
    """Get all connected AA feeds + uploaded bank statements (without file bytes)."""
    if not is_mongo_available():
        return {"applicant_id": applicant_id, "statements": [], "aa_feeds": []}

    statements = await get_bank_statements_for_applicant(applicant_id)
    aa_feeds = await get_aa_feeds_for_applicant(applicant_id)

    return {
        "applicant_id": applicant_id,
        "statements": statements,
        "aa_feeds": aa_feeds,
        "total_statements": len(statements),
        "total_aa_feeds": len(aa_feeds),
    }
