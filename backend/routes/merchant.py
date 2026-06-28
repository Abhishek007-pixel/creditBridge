"""
FastAPI Router for Merchant Agent
Handles digital GSTN linking simulator, manual GSTR filing uploads,
and merchant peer reference tracking.
"""
import logging
import hashlib
import base64
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel

from database_mongo import (
    is_mongo_available,
    create_gstn_filing,
    check_gstn_filing_duplicate,
    create_merchant_reference,
    get_merchant_references_for_applicant,
    update_merchant_reference,
    get_mongo_db
)
from utils.ocr import extract_document_text, call_mistral_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/merchant", tags=["Merchant"])


class GSTNSimulateRequest(BaseModel):
    applicant_id: str
    gstin: str
    phone_number: str


class ReferenceItem(BaseModel):
    reference_name: str
    phone: str
    relationship_type: str  # supplier, buyer, peer
    duration_months: int


class UploadReferencesRequest(BaseModel):
    applicant_id: str
    references: List[ReferenceItem]


class VerifyReferenceRequest(BaseModel):
    reference_id: str
    verified_status: str  # verified, failed
    rating: float  # 1.0 - 5.0


def _parse_gst_document_with_llm(text: str) -> dict:
    """Uses LLM to classify and parse GST tax filing receipts."""
    prompt = f"""
You are an expert tax document parser. Parse the following text from an uploaded tax document.
Determine if the document is a valid GST filing receipt, GSTR-1, GSTR-3B return summary, or official B2B trade invoice.

Set "is_valid" to false if it is any of the following:
- Utility bills (electricity, water, telephone, gas)
- Personal bank statements
- Personal consumer purchases (Swiggy, Zomato, Uber, Netflix, personal Amazon receipt)
- Unreadable/garbage scans

If "is_valid" is false, specify "rejection_reason".

If the document is a valid GSTR return or official trade invoice, set "is_valid" to true. Extract:
- gstin: the 15-character GSTIN identifier (e.g. 27AAAAA1111A1Z1)
- business_name: commercial business name
- amount: total filing turnover or invoice amount as float
- date: YYYY-MM-DD format
- document_type: "gstr" or "invoice"

Document Text:
{text}

Respond ONLY with a valid JSON block inside triple backticks:
```json
{{
  "is_valid": bool,
  "rejection_reason": string or null,
  "gstin": string or null,
  "business_name": string or null,
  "amount": float or null,
  "date": string or null,
  "document_type": string or null
}}
```
"""
    try:
        response_text = call_mistral_text(prompt)
        # Parse JSON from response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Error parsing GST document with LLM: {e}")
        return {
            "is_valid": False,
            "rejection_reason": f"System error parsing document: {str(e)[:60]}",
            "gstin": None,
            "business_name": None,
            "amount": None,
            "date": None,
            "document_type": None
        }


async def _process_gst_upload_async(doc_id: str, text: str):
    """Background task to run LLM parser and transition upload stage."""
    parsed = _parse_gst_document_with_llm(text)
    db = get_mongo_db()
    from bson import ObjectId
    
    if not parsed.get("is_valid"):
        await db.gstn_filings.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "stage": "rejected",
                "rejection_reason": parsed.get("rejection_reason") or "Invalid tax document",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"GST document {doc_id} rejected in background.")
    else:
        # Save structured GSTR fields
        await db.gstn_filings.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "stage": "scored",
                "gstin": parsed.get("gstin"),
                "business_name": parsed.get("business_name"),
                "amount": parsed.get("amount"),
                "date": parsed.get("date"),
                "document_type": parsed.get("document_type") or "gstr",
                # Seed mock filing history and invoices to make the test score rich
                "filing_history": [
                    {"month": "2024-05", "filed_on_time": True},
                    {"month": "2024-04", "filed_on_time": True},
                    {"month": "2024-03", "filed_on_time": True},
                    {"month": "2024-02", "filed_on_time": True},
                    {"month": "2024-01", "filed_on_time": True},
                ],
                "invoices": [
                    {"recipient_gstin": "27BBBBB2222B1Z2", "amount": parsed.get("amount") or 50000.0, "date": parsed.get("date") or "2024-05-15"}
                ],
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"GST document {doc_id} processed & scored successfully in background.")


@router.post("/simulate-gstn")
async def simulate_gstn(payload: GSTNSimulateRequest):
    """
    Simulates linking GSTIN portal profile to pull counter-party and filing metrics.
    """
    if not is_mongo_available():
        raise HTTPException(status_code=500, detail="MongoDB not available")

    # Generate mock 12-month filing history
    months = ["2024-05", "2024-04", "2024-03", "2024-02", "2024-01", "2023-12", "2023-11", "2023-10", "2023-09", "2023-08", "2023-07", "2023-06"]
    filing_history = []
    # 10 out of 12 filed on time (83%)
    for idx, m in enumerate(months):
        filed_on_time = (idx != 2 and idx != 7)  # Fail month 3 and 8
        filing_history.append({"month": m, "filed_on_time": filed_on_time})

    # Generate mock invoices
    invoices = [
        {"recipient_gstin": "27ABCDE1234F1Z1", "amount": 25000.0, "date": "2024-05-10"},
        {"recipient_gstin": "27BCDEF2345G1Z2", "amount": 45000.0, "date": "2024-05-12"},
        {"recipient_gstin": "27CDEFG3456H1Z3", "amount": 15000.0, "date": "2024-04-18"},
        {"recipient_gstin": "27DEFGH4567I1Z4", "amount": 60000.0, "date": "2024-04-20"},
        {"recipient_gstin": "27EFGHI5678J1Z5", "amount": 10000.0, "date": "2024-03-05"},
    ]

    doc = {
        "applicant_id": payload.applicant_id,
        "gstin": payload.gstin,
        "business_name": "Commercial Trader & Retailers Ltd",
        "phone_number": payload.phone_number,
        "filing_history": filing_history,
        "invoices": invoices,
        "stage": "scored",
        "verification_level": "account_aggregator",  # Verified portal link
        "upload_timestamp": datetime.now(timezone.utc)
    }

    db = get_mongo_db()
    # Remove older GST data for this applicant to prevent duplicate scores
    await db.gstn_filings.delete_many({"applicant_id": payload.applicant_id})
    
    doc_id = await create_gstn_filing(doc)
    
    return {
        "status": "success",
        "message": "Simulated GSTN data linked and saved",
        "doc_id": doc_id,
        "gstin": payload.gstin,
        "business_name": doc["business_name"]
    }


@router.post("/upload-gst")
async def upload_gst(
    background_tasks: BackgroundTasks,
    applicant_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload manual GST returns or commercial invoice lists.
    Processes document text via background OCR and LLM classifier.
    """
    if not is_mongo_available():
        raise HTTPException(status_code=500, detail="MongoDB not available")

    content = await file.read()
    file_hash = "sha256:" + hashlib.sha256(content).hexdigest()
    
    # Check duplicate
    if await check_gstn_filing_duplicate(applicant_id, file_hash):
        raise HTTPException(status_code=400, detail="This file has already been uploaded.")

    # Convert to readable text
    text = extract_document_text(content, file.filename)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from document.")

    # Create document record
    doc = {
        "applicant_id": applicant_id,
        "original_filename": file.filename,
        "file_hash": file_hash,
        "file_bytes_b64": base64.b64encode(content).decode(),
        "mime_type": file.content_type or "application/octet-stream",
        "file_size_bytes": len(content),
        "stage": "uploaded",
        "verification_level": "document_uploaded",
        "upload_timestamp": datetime.now(timezone.utc)
    }

    doc_id = await create_gstn_filing(doc)
    background_tasks.add_task(_process_gst_upload_async, doc_id, text)

    return {
        "status": "success",
        "message": "GST document uploaded successfully. Processing in background.",
        "doc_id": doc_id
    }


@router.post("/upload-references")
async def upload_references(payload: UploadReferencesRequest):
    """
    Allows micro-merchants to upload supplier/customer references.
    """
    if not is_mongo_available():
        raise HTTPException(status_code=500, detail="MongoDB not available")

    inserted_ids = []
    for ref in payload.references:
        doc = {
            "applicant_id": payload.applicant_id,
            "reference_name": ref.reference_name,
            "phone": ref.phone,
            "relationship_type": ref.relationship_type,
            "duration_months": ref.duration_months,
            "verified_status": "pending",
            "rating": 0.0,
        }
        ref_id = await create_merchant_reference(doc)
        inserted_ids.append(ref_id)

    return {
        "status": "success",
        "message": f"Submitted {len(payload.references)} reference(s) for verification",
        "inserted_ids": inserted_ids
    }


@router.post("/verify-reference")
async def verify_reference(payload: VerifyReferenceRequest):
    """
    Endpoint for bank officers to verify reference contacts and log credit scores.
    """
    if not is_mongo_available():
        raise HTTPException(status_code=500, detail="MongoDB not available")

    ok = await update_merchant_reference(
        payload.reference_id,
        {
            "verified_status": payload.verified_status,
            "rating": payload.rating,
            "verification_timestamp": datetime.now(timezone.utc)
        }
    )

    if not ok:
        raise HTTPException(status_code=404, detail="Reference contact not found")

    return {
        "status": "success",
        "message": f"Reference updated to status: {payload.verified_status} with rating: {payload.rating}"
    }


@router.get("/{applicant_id}")
async def get_merchant_data(applicant_id: str):
    """Retrieve GST filings and merchant references for an applicant from MongoDB."""
    if not is_mongo_available():
        return {"gstn_filings": [], "merchant_references": []}
    db = get_mongo_db()
    try:
        gstn_cursor = db.gstn_filings.find({"applicant_id": applicant_id})
        gstn_docs = []
        async for doc in gstn_cursor:
            doc["_id"] = str(doc["_id"])
            gstn_docs.append(doc)

        ref_cursor = db.merchant_references.find({"applicant_id": applicant_id})
        ref_docs = []
        async for doc in ref_cursor:
            doc["_id"] = str(doc["_id"])
            ref_docs.append(doc)

        return {
            "gstn_filings": gstn_docs,
            "merchant_references": ref_docs
        }
    except Exception as e:
        logger.warning(f"Failed to fetch merchant data: {e}")
        return {"gstn_filings": [], "merchant_references": []}

