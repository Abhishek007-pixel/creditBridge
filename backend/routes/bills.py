"""
Bill Upload Routes — /api/bills/*
Handles file upload, async processing pipeline, and bill retrieval.

Processing pipeline (runs as background task):
  Stage 1: Validate (type, size, hash dedup)
  Stage 2: Extract text (pdfplumber for text PDFs, Mistral OCR for images/scanned)
  Stage 3: LLM classify (is this a real bill? what type?)
  Stage 4: LLM extract structured fields (amount, date, payee, period)
  Stage 5: Consistency score computation
  Stage 6: Save final scored document + upsert bill_stream
"""
import io
import json
import hashlib
import base64
import logging
import asyncio
import re
import statistics
from calendar import month_abbr
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Header
from pydantic import BaseModel

from database_mongo import (
    is_mongo_available,
    get_mongo_db,
    create_bill_document,
    get_bill_documents_for_applicant,
    update_bill_document,
    check_file_duplicate,
    upsert_bill_stream,
    get_bill_streams_for_applicant,
)
from database import get_db, log_audit
from config import MISTRAL_API_KEY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bills", tags=["bills"])

# ── Constants ─────────────────────────────────────────────────────────────
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024   # 5MB
MAX_FILES_PER_APPLICANT = 10

ACCEPTED_BILL_TYPES = {
    "rent_receipt", "electricity", "water", "gas", "phone",
    "school_fees", "emi_receipt", "insurance_premium",
    "bank_statement", "municipal_tax",
}

MISTRAL_OCR_MODEL = "mistral-ocr-latest"
MISTRAL_TEXT_MODEL = "mistral-medium-latest"
MISTRAL_API_BASE = "https://api.mistral.ai/v1"


# ── Helpers ───────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _call_mistral_text(prompt: str, max_tokens: int = 512) -> str:
    """Call Mistral text API via HTTP (no SDK — avoids dependency conflicts)."""
    resp = requests.post(
        f"{MISTRAL_API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MISTRAL_TEXT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_mistral_ocr(image_b64: str, mime_type: str = "image/jpeg") -> str:
    """
    Call Mistral OCR API to extract text from an image.
    Uses mistral-ocr-latest which is designed for document OCR.
    """
    resp = requests.post(
        f"{MISTRAL_API_BASE}/ocr",
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MISTRAL_OCR_MODEL,
            "document": {
                "type": "image_url",
                "image_url": f"data:{mime_type};base64,{image_b64}",
            },
        },
        timeout=60,
    )
    if resp.status_code == 200:
        data = resp.json()
        # Extract text from pages
        pages = data.get("pages", [])
        return "\n".join(p.get("markdown", "") for p in pages)
    else:
        logger.warning(f"OCR API returned {resp.status_code}: {resp.text[:200]}")
        return ""


def _extract_text_from_pdf(file_bytes: bytes) -> tuple[str, str]:
    """
    Try pdfplumber first (fast, for PDFs with text layer).
    Fall back to Mistral OCR if text is too sparse (scanned PDF).
    Returns (text, method_used).
    """
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(
                (page.extract_text() or "") for page in pdf.pages
            )
        if len(text.strip()) > 50:
            return text, "pdfplumber"
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Fallback: send as base64 image to OCR (treat PDF as image-like)
    b64 = base64.b64encode(file_bytes).decode()
    text = _call_mistral_ocr(b64, mime_type="application/pdf")
    return text, "mistral_ocr"


def _extract_text_from_image(file_bytes: bytes, mime_type: str) -> tuple[str, str]:
    """OCR an image using Mistral OCR API."""
    b64 = base64.b64encode(file_bytes).decode()
    text = _call_mistral_ocr(b64, mime_type=mime_type)
    return text, "mistral_ocr"


def _extract_text_from_csv(file_bytes: bytes, extension: str) -> tuple[str, str]:
    """
    Stage 2C: CSV or Excel structured data.
    Reads with pandas, converts to a text summary for the LLM.
    """
    try:
        import pandas as pd
        if extension in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(file_bytes), nrows=50)
        else:
            df = pd.read_csv(io.BytesIO(file_bytes), nrows=50)

        # Convert to readable text for LLM
        summary_lines = []
        summary_lines.append(f"Columns: {', '.join(str(c) for c in df.columns.tolist())}")
        summary_lines.append(f"Rows: {len(df)}")
        summary_lines.append("---")
        # Show first 20 rows as text
        for _, row in df.head(20).iterrows():
            summary_lines.append(" | ".join(str(v) for v in row.values))
        return "\n".join(summary_lines), "pandas_csv"
    except ImportError:
        return "", "csv_no_pandas"
    except Exception as e:
        logger.warning(f"CSV extraction failed: {e}")
        return "", "csv_error"


def _classify_document(raw_text: str) -> dict:
    """
    Ask Mistral to classify whether this is a valid bill and what type.
    Returns {bill_type, is_valid, confidence, rejection_reason}.
    """
    prompt = f"""You are a document classifier for a credit scoring system.
Analyze this document text and classify it.

ACCEPTED bill types: rent_receipt, electricity, water, gas, phone,
school_fees, emi_receipt, insurance_premium, bank_statement, municipal_tax

REJECTED if: not a financial bill, blank, screenshot of non-financial content,
date older than 24 months, amount is 0.

Document text:
---
{raw_text[:3000]}
---

Respond with ONLY valid JSON, no explanation:
{{
  "bill_type": "<type from accepted list or 'unknown'>",
  "is_valid": <true or false>,
  "confidence": <0.0 to 1.0>,
  "rejection_reason": "<null or reason string>"
}}"""

    try:
        response = _call_mistral_text(prompt, max_tokens=200)
        # Extract JSON from response
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            result = json.loads(match.group())
            result["bill_type"] = result.get("bill_type", "unknown")
            result["is_valid"] = bool(result.get("is_valid", False))
            result["confidence"] = float(result.get("confidence", 0.5))
            return result
    except Exception as e:
        logger.warning(f"Classification failed: {e}")

    return {
        "bill_type": "unknown",
        "is_valid": False,
        "confidence": 0.0,
        "rejection_reason": "LLM classification failed",
    }


def _extract_structured_fields(raw_text: str, bill_type: str) -> dict:
    """
    Ask Mistral to extract structured fields from the bill text.
    Returns {amount, currency, payment_date, billing_period, payee_name, payer_name, is_recurring}.
    """
    prompt = f"""You are extracting structured data from a {bill_type.replace('_', ' ')} document.

Document text:
---
{raw_text[:3000]}
---

Extract these fields. Use null if a field cannot be found.
Respond with ONLY valid JSON:
{{
  "amount": <number or null>,
  "currency": "INR",
  "payment_date": "<YYYY-MM-DD or null>",
  "billing_period": "<e.g. 'January 2024' or null>",
  "payee_name": "<organization/person paid to or null>",
  "payer_name": "<person who paid or null>",
  "is_recurring": <true or false>
}}"""

    try:
        response = _call_mistral_text(prompt, max_tokens=300)
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.warning(f"Field extraction failed: {e}")

    return {
        "amount": None,
        "currency": "INR",
        "payment_date": None,
        "billing_period": None,
        "payee_name": None,
        "payer_name": None,
        "is_recurring": False,
    }


def _compute_stream_score_simple(
    bill_type: str,
    months_covered: int,
    avg_amount: float,
    verification_level: str,
    num_gaps: int = 0,
) -> int:
    """Scoring formula from BILL_AGENT_POV.md."""
    BILL_TYPE_WEIGHTS = {
        "rent_receipt": 1.5, "emi_receipt": 1.4, "school_fees": 1.3,
        "municipal_tax": 1.2, "insurance_premium": 1.1, "electricity": 1.0,
        "water": 0.9, "gas": 0.9, "phone": 0.7,
    }
    VERIFICATION_BONUS = {
        "bank_statement": 10, "account_aggregator": 10,
        "document_uploaded": 5, "image_uploaded": 3, "self_reported": 0,
    }

    def amt_signal(a):
        if a < 500:    return 0.3
        if a < 3000:   return 0.6
        if a < 10000:  return 0.9
        return 1.0

    tw  = BILL_TYPE_WEIGHTS.get(bill_type, 1.0)
    # Consistency: penalise each gap by 5%
    con = max(0.0, min(months_covered / 12.0, 1.0) - (num_gaps * 0.05))
    amt = amt_signal(avg_amount)
    ver = VERIFICATION_BONUS.get(verification_level, 0) / 10.0
    raw = tw * 0.35 + con * 0.40 + amt * 0.15 + ver * 0.10
    return min(100, max(0, round(raw / 1.175 * 100)))


# ── Stage 5: Consistency Analysis helpers ─────────────────────────────────

def _parse_billing_period(period_str: str) -> tuple[int, int] | None:
    """
    Parse a billing_period string like 'January 2024' or '2024-01'
    into (year, month_int) for timeline ordering.
    Returns None if unparseable.
    """
    if not period_str:
        return None
    period_str = period_str.strip()

    # Try 'Month YYYY' or 'YYYY-MM'
    import re as _re
    # 'January 2024', 'Jan 2024'
    m = _re.match(r'([A-Za-z]+)\s+(\d{4})', period_str)
    if m:
        month_str, year_str = m.group(1), m.group(2)
        month_abbrs = {abbr.lower(): i for i, abbr in enumerate(month_abbr) if abbr}
        month_int = month_abbrs.get(month_str[:3].lower())
        if month_int:
            return int(year_str), month_int

    # 'YYYY-MM'
    m = _re.match(r'(\d{4})-(\d{2})', period_str)
    if m:
        return int(m.group(1)), int(m.group(2))

    return None


def _compute_consistency_analysis(periods: list[str], amounts: list[float]) -> dict:
    """
    Stage 5 full consistency analysis for a stream.

    Given a list of billing_period strings and corresponding amounts:
    - months_covered: how many distinct periods exist
    - streak: longest run of consecutive calendar months
    - num_gaps: number of missing months in the covered window
    - variance: std deviation of amounts (0 = perfectly consistent)
    - amount_variance_flag: True if variance > 30% of mean (suspicious)
    """
    if not periods:
        return {
            "months_covered": 0,
            "streak": 0,
            "num_gaps": 0,
            "variance": 0.0,
            "amount_variance_flag": False,
            "timeline": [],
        }

    # Parse periods into (year, month) tuples, deduplicate
    parsed = []
    for p in periods:
        ym = _parse_billing_period(p)
        if ym:
            parsed.append(ym)
    parsed = sorted(set(parsed))  # unique, chronological

    months_covered = len(parsed)

    if months_covered == 0:
        return {
            "months_covered": 0,
            "streak": 0,
            "num_gaps": 0,
            "variance": 0.0,
            "amount_variance_flag": False,
            "timeline": [],
        }

    # Build the full expected monthly timeline between min and max date
    def next_month(y, m):
        return (y + 1, 1) if m == 12 else (y, m + 1)

    first_ym = parsed[0]
    last_ym  = parsed[-1]
    present_set = set(parsed)

    full_timeline = []
    cur = first_ym
    while cur <= last_ym:
        full_timeline.append(cur)
        cur = next_month(*cur)

    # Gaps = months in the window that are missing
    missing = [ym for ym in full_timeline if ym not in present_set]
    num_gaps = len(missing)

    # Streak: longest consecutive run in `parsed`
    max_streak = 1
    cur_streak = 1
    for i in range(1, len(parsed)):
        expected = next_month(*parsed[i - 1])
        if parsed[i] == expected:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 1

    # Amount variance (std dev)
    clean_amounts = [a for a in amounts if a and a > 0]
    if len(clean_amounts) >= 2:
        mean_amt = sum(clean_amounts) / len(clean_amounts)
        variance = statistics.stdev(clean_amounts)
        # Flag if std dev > 30% of mean (wild swings = suspicious)
        variance_flag = mean_amt > 0 and (variance / mean_amt) > 0.30
    else:
        variance = 0.0
        variance_flag = False

    # Human-readable timeline string: 'Jan-2024 -> Mar-2024 [gap: Feb-2024]'
    month_names = list(month_abbr)
    timeline_str = " -> ".join(
        f"{month_names[m]}-{y}" for y, m in parsed
    )

    return {
        "months_covered": months_covered,
        "streak": max_streak,
        "num_gaps": num_gaps,
        "variance": round(variance, 2),
        "amount_variance_flag": variance_flag,
        "timeline": timeline_str,
    }


# ── Background processing pipeline ───────────────────────────────────────

async def _process_bill(doc_id: str, file_bytes: bytes, mime_type: str, applicant_id: str, original_ext: str = ""):
    """
    Full 6-stage async pipeline. Runs in background after upload.
    Updates document stage at each step so frontend can show progress.
    """
    if not is_mongo_available():
        logger.error("MongoDB not available — cannot process bill")
        return

    # ── Stage 2: Content Extraction ───────────────────────────────────────
    await update_bill_document(doc_id, {"stage": "extracting"})
    try:
        if mime_type == "application/pdf":
            # Path A: pdfplumber (text PDF) → Path B: Mistral OCR (scanned)
            raw_text, extract_method = _extract_text_from_pdf(file_bytes)
        elif original_ext in (".csv", ".xlsx", ".xls"):
            # Path C: Structured CSV/Excel
            raw_text, extract_method = _extract_text_from_csv(file_bytes, original_ext)
        else:
            # Path B: Image → Mistral OCR
            raw_text, extract_method = _extract_text_from_image(file_bytes, mime_type)
    except Exception as e:
        logger.error(f"Text extraction failed for {doc_id}: {e}")
        await update_bill_document(doc_id, {
            "stage": "rejected",
            "rejection_reason": f"Text extraction failed: {str(e)[:100]}",
        })
        return

    if not raw_text or len(raw_text.strip()) < 20:
        await update_bill_document(doc_id, {
            "stage": "rejected",
            "rejection_reason": "Could not extract readable text from file",
        })
        return

    # ── Stage 3: LLM Content Classification ──────────────────────────────
    await update_bill_document(doc_id, {"stage": "classifying", "extract_method": extract_method})
    classification = await asyncio.to_thread(_classify_document, raw_text)

    if not classification["is_valid"] or classification["confidence"] < 0.6:
        await update_bill_document(doc_id, {
            "stage": "rejected",
            "classification": classification,
            "rejection_reason": classification.get("rejection_reason") or "Low confidence classification",
        })
        return

    bill_type = classification["bill_type"]
    if bill_type not in ACCEPTED_BILL_TYPES:
        await update_bill_document(doc_id, {
            "stage": "rejected",
            "classification": classification,
            "rejection_reason": f"Unrecognized bill type: {bill_type}",
        })
        return

    # ── Stage 4: Structured Extraction (LLM) ─────────────────────────────
    await update_bill_document(doc_id, {"stage": "extracting_fields", "classification": classification})
    extraction = await asyncio.to_thread(_extract_structured_fields, raw_text, bill_type)
    extraction["bill_type"] = bill_type

    verification_level = "document_uploaded"
    if mime_type in ("image/jpeg", "image/jpg", "image/png"):
        verification_level = "image_uploaded"

    # ── Stage 5: Consistency Analysis ────────────────────────────────────
    # Fetch all previously processed bills for this applicant+bill_type+payee
    # to compute the true multi-month consistency timeline.
    await update_bill_document(doc_id, {"stage": "analyzing_consistency"})

    payee = extraction.get("payee_name") or "Unknown"
    amount = extraction.get("amount") or 0
    billing_period = extraction.get("billing_period") or datetime.now().strftime("%B %Y")

    try:
        db = get_mongo_db()
        # Load all scored docs for same applicant + bill_type + payee
        existing_cursor = db.bill_documents.find(
            {
                "applicant_id": applicant_id,
                "stage": "scored",
                "extraction.bill_type": bill_type,
                "extraction.payee_name": payee,
            },
            {"extraction.billing_period": 1, "extraction.amount": 1}
        )
        existing_docs = [d async for d in existing_cursor]

        # Collect all periods + amounts (include current bill being processed)
        all_periods = [billing_period]
        all_amounts = [amount] if amount else []
        for d in existing_docs:
            extr = d.get("extraction") or {}
            p = extr.get("billing_period")
            a = extr.get("amount")
            if p:
                all_periods.append(p)
            if a:
                all_amounts.append(float(a))

        # Run full consistency analysis (streak, gaps, variance)
        consistency = _compute_consistency_analysis(all_periods, all_amounts)

    except Exception as e:
        logger.warning(f"Consistency analysis failed: {e} — using single-bill baseline")
        consistency = {
            "months_covered": 1,
            "streak": 1,
            "num_gaps": 0,
            "variance": 0.0,
            "amount_variance_flag": False,
            "timeline": billing_period,
        }

    months_covered = consistency["months_covered"]
    streak         = consistency["streak"]
    num_gaps       = consistency["num_gaps"]
    variance       = consistency["variance"]
    variance_flag  = consistency["amount_variance_flag"]

    # ── Stage 6: Scoring + Reason Generation ─────────────────────────────
    stream_score = _compute_stream_score_simple(
        bill_type=bill_type,
        months_covered=months_covered,
        avg_amount=sum(all_amounts) / len(all_amounts) if all_amounts else amount,
        verification_level=verification_level,
        num_gaps=num_gaps,
    )

    # Build rich human-readable reason
    bill_label = bill_type.replace("_", " ").title()
    reason_parts = [
        f"{bill_label} — {payee}.",
        f"{months_covered} month(s) covered (streak: {streak} consecutive).",
        f"Avg ₹{(sum(all_amounts)/len(all_amounts) if all_amounts else amount):,.0f}/mo.",
    ]
    if num_gaps > 0:
        reason_parts.append(f"⚠ {num_gaps} gap(s) detected in payment timeline.")
    if variance_flag:
        reason_parts.append(f"⚠ High amount variance (σ=₹{variance:,.0f}) — flagged for review.")
    reason_parts.append(f"Stream score: {stream_score}/100.")
    reason = " ".join(reason_parts)

    # Determine flags
    flags = []
    if num_gaps > 0:
        flags.append({"type": "payment_gaps", "detail": f"{num_gaps} missing month(s)"})
    if variance_flag:
        flags.append({"type": "amount_variance", "detail": f"std dev ₹{variance:,.0f}"})

    # Save fully scored document
    await update_bill_document(doc_id, {
        "stage": "scored",
        "ocr_raw_text": raw_text[:5000],
        "extraction": extraction,
        "verification_level": verification_level,
        "stream_score": stream_score,
        "reason": reason,
        "flags": flags,
        "consistency": consistency,    # full Stage 5 data persisted
    })

    # Upsert bill_stream with full consistency data
    await upsert_bill_stream(
        applicant_id=applicant_id,
        bill_type=bill_type,
        payee_name=payee,
        stream_data={
            "last_amount": amount,
            "last_period": billing_period,
            "last_score": stream_score,
            "last_reason": reason,
            "doc_count": len(existing_docs) + 1,
            "verification_level": verification_level,
            # Stage 5 consistency data
            "months_covered": months_covered,
            "streak": streak,
            "num_gaps": num_gaps,
            "amount_variance": round(variance, 2),
            "amount_variance_flag": variance_flag,
            "timeline": consistency.get("timeline", ""),
        },
    )

    log_audit(applicant_id, "BILL_PROCESSED", {
        "doc_id": doc_id,
        "bill_type": bill_type,
        "stream_score": stream_score,
        "payee": payee,
        "months_covered": months_covered,
        "streak": streak,
        "num_gaps": num_gaps,
    })
    logger.info(
        f"Bill {doc_id} processed — {bill_type}, score={stream_score}, "
        f"months={months_covered}, streak={streak}, gaps={num_gaps}"
    )


# ── Routes ────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_bill(
    background_tasks: BackgroundTasks,
    applicant_id: str = Form(...),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    """
    Upload a bill document (PDF/JPG/PNG) for an applicant.
    Stage 1 validation is synchronous (fast). Processing runs in background.
    Returns immediately with doc_id + 'processing' status.
    """
    if not is_mongo_available():
        raise HTTPException(
            status_code=503,
            detail="Bill upload service unavailable — MongoDB not connected",
        )

    # ── Validate applicant exists in SQLite ───────────────────────────────
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM applicants WHERE id = ?", (applicant_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Applicant not found")

    # ── Stage 1: File validation ──────────────────────────────────────────
    # Check extension
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Accepted: PDF, JPG, PNG",
        )

    # Check MIME type
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in ALLOWED_MIME_TYPES:
        # Be lenient with MIME — trust extension
        ext_to_mime = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }
        mime_type = ext_to_mime.get(ext, mime_type)

    # Read file bytes
    file_bytes = await file.read()

    # Check size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum is 5MB, received {len(file_bytes) // 1024}KB",
        )

    if len(file_bytes) < 100:
        raise HTTPException(status_code=400, detail="File appears to be empty")

    # Check max files per applicant
    db = get_mongo_db()
    existing_count = await db.bill_documents.count_documents({"applicant_id": applicant_id})
    if existing_count >= MAX_FILES_PER_APPLICANT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES_PER_APPLICANT} bill files per applicant reached",
        )

    # Check duplicate (same file hash)
    file_hash = _sha256(file_bytes)
    is_dup = await check_file_duplicate(applicant_id, file_hash)
    if is_dup:
        raise HTTPException(
            status_code=409,
            detail="This file has already been uploaded for this applicant",
        )

    # ── Store document (stage = 'uploaded') ──────────────────────────────
    file_b64 = base64.b64encode(file_bytes).decode()
    doc_id = await create_bill_document({
        "applicant_id":     applicant_id,
        "original_filename": filename,
        "file_hash":        file_hash,
        "file_bytes_b64":   file_b64,
        "mime_type":        mime_type,
        "file_size_bytes":  len(file_bytes),
        "stage":            "uploaded",
        "upload_timestamp": datetime.now(timezone.utc),
        "verification_level": "image_uploaded" if mime_type.startswith("image/") else "document_uploaded",
        "flags":            [],
        "classification":   None,
        "extraction":       None,
        "stream_score":     None,
        "reason":           None,
    })

    log_audit(applicant_id, "BILL_UPLOADED", {
        "doc_id": doc_id,
        "filename": filename,
        "size_bytes": len(file_bytes),
        "mime_type": mime_type,
    })

    # ── Launch async processing pipeline ─────────────────────────────────
    background_tasks.add_task(
        _process_bill, doc_id, file_bytes, mime_type, applicant_id, ext
    )

    return {
        "message": "Bill uploaded successfully. Processing in background.",
        "doc_id": doc_id,
        "filename": filename,
        "stage": "uploaded",
        "applicant_id": applicant_id,
        "file_size_bytes": len(file_bytes),
    }


@router.get("/{applicant_id}")
async def get_applicant_bills(
    applicant_id: str,
    authorization: Optional[str] = Header(None),
):
    """
    Get all bill documents for an applicant (without file bytes).
    Used by frontend to show processing status + results.
    """
    if not is_mongo_available():
        return {"applicant_id": applicant_id, "bills": [], "message": "MongoDB unavailable"}

    docs = await get_bill_documents_for_applicant(applicant_id)
    return {
        "applicant_id": applicant_id,
        "bills": docs,
        "total": len(docs),
        "scored": sum(1 for d in docs if d.get("stage") == "scored"),
        "processing": sum(1 for d in docs if d.get("stage") not in ("scored", "rejected", "uploaded")),
        "rejected": sum(1 for d in docs if d.get("stage") == "rejected"),
    }


@router.get("/{applicant_id}/streams")
async def get_bill_streams(
    applicant_id: str,
    authorization: Optional[str] = Header(None),
):
    """
    Get aggregated bill stream analysis for an applicant.
    Used by BankDashboard to show per-bill-type breakdown.
    """
    if not is_mongo_available():
        return {"applicant_id": applicant_id, "streams": []}

    streams = await get_bill_streams_for_applicant(applicant_id)
    return {
        "applicant_id": applicant_id,
        "streams": streams,
        "stream_count": len(streams),
    }


@router.get("/{applicant_id}/summary")
async def get_bill_summary(applicant_id: str):
    """
    Quick summary for scoring pipeline — returns final aggregated bill score.
    Called internally by BillConsistencyScoringTool and frontend.
    """
    if not is_mongo_available():
        return {"applicant_id": applicant_id, "has_bills": False, "final_score": 45}

    streams = await get_bill_streams_for_applicant(applicant_id)
    if not streams:
        return {"applicant_id": applicant_id, "has_bills": False, "final_score": 45}

    scores = [s.get("last_score", 50) for s in streams]
    unique_types = len(set(s.get("bill_type") for s in streams))
    diversity = min(1.0 + (unique_types - 1) * 0.1, 1.2)
    avg = sum(scores) / len(scores)
    final = min(100, round(avg * diversity))

    return {
        "applicant_id": applicant_id,
        "has_bills": True,
        "final_score": final,
        "stream_count": len(streams),
        "unique_bill_types": unique_types,
    }
