"""
E-commerce Router — /api/ecommerce/*
Handles uploading e-commerce purchase invoices, OCR, LLM extraction,
livelihood asset flags, and MongoDB persistence.
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
    create_ecommerce_invoice,
    update_ecommerce_invoice,
    check_ecommerce_invoice_duplicate,
)
from database import get_db, log_audit
from utils.ocr import call_mistral_text, extract_document_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ecommerce", tags=["ecommerce"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _parse_invoice_with_llm(raw_text: str) -> dict:
    """
    Classify and extract fields from the e-commerce receipt text.
    Rejects: Food (Zomato/Swiggy), cabs (Uber), entertainment (Netflix), or < ₹150.
    Identifies livelihood assets (machinery, tools, agricultural inputs).
    """
    prompt = f"""You are a specialized e-commerce invoice parser and validator.
Analyze the following document text and determine if it is a valid e-commerce purchase or business receipt.

VALID criteria:
- E-commerce purchases (Amazon, Flipkart, Meesho, Myntra, Nykaa, etc.) or local business/hardware/agriculture shops.
- Total amount must be >= 150 INR.

REJECTED criteria:
- Food receipts/deliveries (Zomato, Swiggy, restaurants, etc.)
- Cab rides (Uber, Ola, Rapido, etc.)
- Entertainment subscriptions (Netflix, Spotify, Prime Video, etc.)
- Any receipts with a total amount less than 150 INR.

Document text:
---
{raw_text[:2500]}
---

Respond with ONLY valid JSON, no markdown formatting or extra text.
JSON schema:
{{
  "is_valid": <true or false>,
  "rejection_reason": "<null or explanation why it is rejected>",
  "platform": "<platform name like Amazon, Flipkart, Meesho, or local shop name>",
  "amount": <positive number, representing the final invoice total amount in INR>,
  "payment_method": "<Prepaid | COD | Mixed>",
  "date": "<YYYY-MM-DD or null>",
  "item_description": "<Brief summary of main items purchased>",
  "is_livelihood_asset": <true or false, set to true ONLY if the items are livelihood/business-enabling investments such as machinery, tools, sewing machines, crop seeds, agricultural equipment, or professional toolsets>
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
        logger.error(f"LLM e-commerce parsing failed: {e}")
    
    return {
        "is_valid": False,
        "rejection_reason": "Failed to parse receipt with AI classifier."
    }


async def _process_ecommerce_invoice(doc_id: str, file_bytes: bytes, mime_type: str, applicant_id: str, ext: str):
    if not is_mongo_available():
        return

    await update_ecommerce_invoice(doc_id, {"stage": "extracting"})

    try:
        # Extract text using shared OCR helper
        raw_text, extract_method = extract_document_text(file_bytes, mime_type, ext)

        if not raw_text or len(raw_text.strip()) < 20:
            await update_ecommerce_invoice(doc_id, {
                "stage": "rejected",
                "rejection_reason": "Failed to extract readable text from receipt."
            })
            return

        # Stage 3/4: LLM Parse & Classify
        await update_ecommerce_invoice(doc_id, {"stage": "parsing_invoice", "extract_method": extract_method})
        parsed = await asyncio.to_thread(_parse_invoice_with_llm, raw_text)

        if not parsed.get("is_valid", False):
            await update_ecommerce_invoice(doc_id, {
                "stage": "rejected",
                "rejection_reason": parsed.get("rejection_reason") or "Invoice did not meet validity criteria."
            })
            log_audit(applicant_id, "ECOMMERCE_INVOICE_REJECTED", {
                "doc_id": doc_id,
                "reason": parsed.get("rejection_reason")
            })
            return

        # Stage 5/6: Scored / Saved
        await update_ecommerce_invoice(doc_id, {
            "stage": "scored",
            "platform": parsed.get("platform"),
            "amount": parsed.get("amount"),
            "payment_method": parsed.get("payment_method"),
            "date": parsed.get("date"),
            "item_description": parsed.get("item_description"),
            "is_livelihood_asset": parsed.get("is_livelihood_asset"),
        })

        log_audit(applicant_id, "ECOMMERCE_INVOICE_PROCESSED", {
            "doc_id": doc_id,
            "platform": parsed.get("platform"),
            "amount": parsed.get("amount"),
            "is_livelihood_asset": parsed.get("is_livelihood_asset"),
        })
        logger.info(f"E-commerce invoice {doc_id} processed successfully — Platform: {parsed.get('platform')}")

    except Exception as e:
        logger.error(f"E-commerce pipeline error on {doc_id}: {e}")
        await update_ecommerce_invoice(doc_id, {
            "stage": "rejected",
            "rejection_reason": f"Unexpected pipeline failure: {str(e)[:100]}"
        })


@router.post("/upload")
async def upload_ecommerce_invoice(
    background_tasks: BackgroundTasks,
    applicant_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload an e-commerce invoice (Amazon/Flipkart receipt). Background parsed."""
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
    is_dup = await check_ecommerce_invoice_duplicate(applicant_id, file_hash)
    if is_dup:
        raise HTTPException(status_code=409, detail="Duplicate invoice file already uploaded.")

    # Save initial record to MongoDB
    file_b64 = base64.b64encode(file_bytes).decode()
    mime_type = file.content_type or "application/octet-stream"

    doc_id = await create_ecommerce_invoice({
        "applicant_id": applicant_id,
        "original_filename": filename,
        "file_hash": file_hash,
        "file_bytes_b64": file_b64,
        "mime_type": mime_type,
        "file_size_bytes": len(file_bytes),
        "stage": "uploaded",
    })

    log_audit(applicant_id, "ECOMMERCE_INVOICE_UPLOADED", {
        "doc_id": doc_id,
        "filename": filename,
    })

    # Start parsing pipeline
    background_tasks.add_task(
        _process_ecommerce_invoice, doc_id, file_bytes, mime_type, applicant_id, ext
    )

    return {
        "message": "Ecommerce invoice uploaded. Processing in background.",
        "doc_id": doc_id,
        "stage": "uploaded",
    }
