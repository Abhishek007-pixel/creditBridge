"""
FastAPI Router for Geolocation Agent
Handles live GPS verification and Aadhaar address proof uploads.
"""
import logging
import hashlib
import base64
import json
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel

from database_mongo import (
    is_mongo_available,
    create_aadhaar_address,
    create_gps_verification,
    get_mongo_db
)
from utils.ocr import extract_document_text, call_mistral_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geolocation", tags=["Geolocation"])


class GPSVerifyRequest(BaseModel):
    applicant_id: str
    latitude: float
    longitude: float


def _simulate_reverse_geocode(lat: float, lon: float) -> dict:
    """Simulates reverse geocoding of coordinates into Indian cities and PIN codes."""
    # List of reference coordinates
    cities = [
        {"name": "Delhi", "state": "Delhi", "pin_code": "110001", "lat": 28.6139, "lon": 77.2090},
        {"name": "Mumbai", "state": "Maharashtra", "pin_code": "400001", "lat": 18.9750, "lon": 72.8258},
        {"name": "Bangalore", "state": "Karnataka", "pin_code": "560001", "lat": 12.9716, "lon": 77.5946},
        {"name": "Guwahati", "state": "Assam", "pin_code": "781001", "lat": 26.1445, "lon": 91.7362},
    ]
    
    # Find closest reference city
    closest = cities[0]
    min_dist = float('inf')
    for c in cities:
        dist = ((lat - c["lat"])**2 + (lon - c["lon"])**2)**0.5
        if dist < min_dist:
            min_dist = dist
            closest = c
            
    # If the distance is too large (> 3 degrees), return a default out-of-region zone
    if min_dist > 3.0:
        return {
            "city": "Unknown Region",
            "state": "Out of India/Remote",
            "pin_code": "000000",
            "dist_km": round(min_dist * 111, 1)
        }
        
    return {
        "city": closest["name"],
        "state": closest["state"],
        "pin_code": closest["pin_code"],
        "dist_km": round(min_dist * 111, 1)
    }


def _parse_aadhaar_with_llm(text: str) -> dict:
    """Uses LLM to validate and structure Aadhaar address text."""
    prompt = f"""
You are an expert identity document parser. Parse the following text extracted from the back side of an Indian Aadhaar Card (the address block).
Determine if the document contains a valid Aadhaar registered address.

If the document does not look like an Indian Aadhaar card address card, or is completely unreadable, set "is_valid" to false and provide a "rejection_reason".

If the document is a valid Aadhaar address card, set "is_valid" to true. Extract the following address details:
- city: City/Town/Village name
- state: State name (e.g. Maharashtra, Assam, Karnataka, Delhi)
- pin_code: 6-digit numerical PIN code (e.g. 400001, 781001)
- street: Street name/Locality if present, or null

Document Text:
{text}

Respond ONLY with a valid JSON block inside triple backticks:
```json
{{
  "is_valid": bool,
  "rejection_reason": string or null,
  "city": string or null,
  "state": string or null,
  "pin_code": string or null,
  "street": string or null
}}
```
"""
    try:
        response_text = call_mistral_text(prompt)
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Error parsing Aadhaar with LLM: {e}")
        return {
            "is_valid": False,
            "rejection_reason": f"Parsing failure: {str(e)[:60]}",
            "city": None,
            "state": None,
            "pin_code": None,
            "street": None
        }


async def _process_aadhaar_upload_async(doc_id: str, text: str):
    """Background task to run LLM parser and update Aadhaar stage."""
    parsed = _parse_aadhaar_with_llm(text)
    db = get_mongo_db()
    from bson import ObjectId
    
    if not parsed.get("is_valid"):
        await db.aadhaar_addresses.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "stage": "rejected",
                "rejection_reason": parsed.get("rejection_reason") or "Invalid Aadhaar document",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"Aadhaar document {doc_id} rejected in background.")
    else:
        await db.aadhaar_addresses.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "stage": "scored",
                "city": parsed.get("city"),
                "state": parsed.get("state"),
                "pin_code": parsed.get("pin_code"),
                "street": parsed.get("street"),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        logger.info(f"Aadhaar document {doc_id} parsed & scored successfully in background.")


@router.post("/upload-aadhaar")
async def upload_aadhaar(
    background_tasks: BackgroundTasks,
    applicant_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload manual Aadhaar address back scan.
    Processes text via background OCR and LLM classifier.
    """
    if not is_mongo_available():
        raise HTTPException(status_code=500, detail="MongoDB not available")

    content = await file.read()
    file_hash = "sha256:" + hashlib.sha256(content).hexdigest()
    
    # Check duplicate
    db = get_mongo_db()
    existing = await db.aadhaar_addresses.find_one({
        "applicant_id": applicant_id,
        "file_hash": file_hash
    })
    if existing:
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
        "stage": "uploaded",
        "upload_timestamp": datetime.now(timezone.utc)
    }

    doc_id = await create_aadhaar_address(doc)
    background_tasks.add_task(_process_aadhaar_upload_async, doc_id, text)

    return {
        "status": "success",
        "message": "Aadhaar document uploaded successfully. Processing in background.",
        "doc_id": doc_id
    }


@router.post("/verify-gps")
async def verify_gps(payload: GPSVerifyRequest):
    """
    Accepts device Geolocation coordinates and reverse-geocodes them to capture live location.
    """
    if not is_mongo_available():
        raise HTTPException(status_code=500, detail="MongoDB not available")

    resolved = _simulate_reverse_geocode(payload.latitude, payload.longitude)
    
    doc = {
        "applicant_id": payload.applicant_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "city": resolved["city"],
        "state": resolved["state"],
        "pin_code": resolved["pin_code"],
        "timestamp": datetime.now(timezone.utc)
    }
    
    # Clear older GPS entries to avoid old location bias
    db = get_mongo_db()
    await db.gps_verifications.delete_many({"applicant_id": payload.applicant_id})
    
    doc_id = await create_gps_verification(doc)
    
    return {
        "status": "success",
        "message": "Device live location verified successfully",
        "doc_id": doc_id,
        "resolved_city": resolved["city"],
        "resolved_pin_code": resolved["pin_code"]
    }
