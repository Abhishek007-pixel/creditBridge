"""
Financial Commitments Router — /api/commitments/*
Handles uploading policy documents, premium receipts, SIP statements, chit funds,
and RD/FD certificates, extracting structured fields via LLM, and persisting in MongoDB.
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

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from database_mongo import (
    is_mongo_available,
    create_financial_commitment,
    update_financial_commitment,
    check_financial_commitment_duplicate,
)
from database import get_db, log_audit
from utils.ocr import call_mistral_text, extract_document_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/commitments", tags=["commitments"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _parse_commitment_with_llm(raw_text: str) -> dict:
    """
    Classify and extract savings/premium commitment fields.
    Allowed: Insurance premium receipts, Mutual Fund SIP statements, RD/FD certificates, chit funds.
    Rejects: Generic bank statements, utility bills, salary statements.
    """
    prompt = f"""You are a specialized financial commitment document parser and validator.
Analyze the following text and determine if it represents a valid long-term savings or insurance commitment receipt/certificate.

VALID categories:
- Insurance policy premium receipts (e.g. LIC, HDFC Life, ICICI Pru, SBI Life, etc.)
- Mutual Fund SIP statements or installment receipts.
- Recurring Deposit (RD) or Fixed Deposit (FD) certificates or ledger entries.
- Chit fund passbooks or payment receipts.

REJECTED categories:
- Generic monthly bank statements.
- Utility bills (electricity, water, gas, phone).
- Salary statements/slips.
- Any other non-savings/non-insurance documents.

Document text:
---
{raw_text[:2500]}
---

Respond with ONLY valid JSON, no markdown formatting or extra text.
JSON schema:
{{
  "is_valid": <true or false>,
  "rejection_reason": "<null or explanation why it is rejected>",
  "provider": "<financial institution or insurance provider name, e.g. LIC India, Nippon India Mutual Fund, SBI, etc.>",
  "amount": <positive number, representing the premium/SIP/deposit payment amount in INR>,
  "payment_date": "<YYYY-MM-DD or null>",
  "policy_type": "<insurance | sip | chit_fund | deposit>",
  "period": "<e.g. 'June 2024', 'Annual', 'Monthly', 'Q1 2024', or null>"
}}"""

    try:
        response = call_mistral_text(prompt, max_tokens=300)
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            result = json.loads(match.group())
            # Ensure proper schema fields
            result.setdefault("is_valid", False)
            result.setdefault("rejection_reason", "Invalid response structure")
            return result
    except Exception as e:
        logger.error(f"LLM commitment parsing failed: {e}")
    
    return {
        "is_valid": False,
        "rejection_reason": "Failed to parse commitment document with AI classifier."
    }


async def _process_financial_commitment(doc_id: str, file_bytes: bytes, mime_type: str, applicant_id: str, ext: str):
    if not is_mongo_available():
        return

    await update_financial_commitment(doc_id, {"stage": "extracting"})

    try:
        # Extract text using shared OCR helper
        raw_text, extract_method = extract_document_text(file_bytes, mime_type, ext)

        if not raw_text or len(raw_text.strip()) < 20:
            await update_financial_commitment(doc_id, {
                "stage": "rejected",
                "rejection_reason": "Failed to extract readable text from document."
            })
            return

        # Stage 3/4: LLM Parse & Classify
        await update_financial_commitment(doc_id, {"stage": "parsing_commitment", "extract_method": extract_method})
        parsed = await asyncio.to_thread(_parse_commitment_with_llm, raw_text)

        if not parsed.get("is_valid", False):
            await update_financial_commitment(doc_id, {
                "stage": "rejected",
                "rejection_reason": parsed.get("rejection_reason") or "Document did not meet validity criteria."
            })
            log_audit(applicant_id, "FINANCIAL_COMMITMENT_REJECTED", {
                "doc_id": doc_id,
                "reason": parsed.get("rejection_reason")
            })
            return

        # Stage 5/6: Scored / Saved
        await update_financial_commitment(doc_id, {
            "stage": "scored",
            "provider": parsed.get("provider"),
            "amount": parsed.get("amount"),
            "payment_date": parsed.get("payment_date"),
            "policy_type": parsed.get("policy_type"),
            "period": parsed.get("period"),
        })

        log_audit(applicant_id, "FINANCIAL_COMMITMENT_PROCESSED", {
            "doc_id": doc_id,
            "provider": parsed.get("provider"),
            "amount": parsed.get("amount"),
            "policy_type": parsed.get("policy_type"),
        })
        logger.info(f"Financial commitment {doc_id} processed successfully — Provider: {parsed.get('provider')}")

    except Exception as e:
        logger.error(f"Financial commitment pipeline error on {doc_id}: {e}")
        await update_financial_commitment(doc_id, {
            "stage": "rejected",
            "rejection_reason": f"Unexpected pipeline failure: {str(e)[:100]}"
        })


@router.post("/upload")
async def upload_financial_commitment(
    background_tasks: BackgroundTasks,
    applicant_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload a savings/commitment payment document. Background parsed."""
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
    is_dup = await check_financial_commitment_duplicate(applicant_id, file_hash)
    if is_dup:
        raise HTTPException(status_code=409, detail="Duplicate commitment file already uploaded.")

    # Save initial record to MongoDB
    file_b64 = base64.b64encode(file_bytes).decode()
    mime_type = file.content_type or "application/octet-stream"

    doc_id = await create_financial_commitment({
        "applicant_id": applicant_id,
        "original_filename": filename,
        "file_hash": file_hash,
        "file_bytes_b64": file_b64,
        "mime_type": mime_type,
        "file_size_bytes": len(file_bytes),
        "stage": "uploaded",
    })

    log_audit(applicant_id, "FINANCIAL_COMMITMENT_UPLOADED", {
        "doc_id": doc_id,
        "filename": filename,
    })

    # Start parsing pipeline
    background_tasks.add_task(
        _process_financial_commitment, doc_id, file_bytes, mime_type, applicant_id, ext
    )

    return {
        "message": "Financial commitment uploaded. Processing in background.",
        "doc_id": doc_id,
        "stage": "uploaded",
    }
