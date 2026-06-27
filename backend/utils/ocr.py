"""
Shared OCR and Text Extraction Utilities
Used across Bills, Cashflow, Ecommerce, and Financial Commitment agents.
Reuses Mistral OCR API and local pdfplumber / pandas parsers.
"""
import io
import os
import base64
import logging
import requests

from config import MISTRAL_API_KEY

logger = logging.getLogger(__name__)

MISTRAL_TEXT_MODEL = "mistral-medium-latest"
MISTRAL_OCR_MODEL = "mistral-ocr-latest"
MISTRAL_API_BASE = "https://api.mistral.ai/v1"


def call_mistral_text(prompt: str, max_tokens: int = 500) -> str:
    """Call Mistral chat API directly via HTTP request."""
    try:
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
            timeout=40,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Mistral chat API error: {e}")
        raise


def call_mistral_ocr(image_b64: str, mime_type: str) -> str:
    """Call Mistral OCR API to extract text layout from a PDF page or image."""
    try:
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
            pages = resp.json().get("pages", [])
            return "\n".join(p.get("markdown", "") for p in pages)
        else:
            logger.warning(f"OCR API returned status {resp.status_code}: {resp.text[:200]}")
            return ""
    except Exception as e:
        logger.error(f"Mistral OCR connection error: {e}")
        return ""


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, str]:
    """Extract text from PDF file. Falls back to OCR if text is sparse."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        if len(text.strip()) > 50:
            return text, "pdfplumber"
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Fallback to OCR
    b64 = base64.b64encode(file_bytes).decode()
    text = call_mistral_ocr(b64, "application/pdf")
    return text, "mistral_ocr"


def extract_text_from_image(file_bytes: bytes, mime_type: str) -> tuple[str, str]:
    """OCR an image file using Mistral OCR API."""
    b64 = base64.b64encode(file_bytes).decode()
    text = call_mistral_ocr(b64, mime_type)
    return text, "mistral_ocr"


def extract_text_from_csv(file_bytes: bytes, extension: str) -> tuple[str, str]:
    """Convert CSV or Excel spreadsheet records to readable text lines for LLM."""
    try:
        import pandas as pd
        if extension in (".xlsx", ".xls"):
            df = pd.read_excel(io.BytesIO(file_bytes), nrows=40)
        else:
            df = pd.read_csv(io.BytesIO(file_bytes), nrows=40)

        summary = [
            f"Columns: {', '.join(str(c) for c in df.columns)}",
            f"Rows count: {len(df)}",
            "---"
        ]
        for _, row in df.head(20).iterrows():
            summary.append(" | ".join(str(v) for v in row.values))
        return "\n".join(summary), "pandas_csv"
    except Exception as e:
        logger.warning(f"CSV extraction failed: {e}")
        return "", "csv_error"


def extract_document_text(file_bytes: bytes, mime_type: str, extension: str) -> tuple[str, str]:
    """General utility to route text extraction by file type."""
    mime_type = mime_type.lower()
    extension = extension.lower()

    if mime_type == "application/pdf" or extension == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif mime_type == "text/plain" or extension == ".txt":
        raw = file_bytes.decode("utf-8", errors="ignore")
        return raw, "plain_text"
    elif extension in (".csv", ".xlsx", ".xls") or "csv" in mime_type or "excel" in mime_type:
        return extract_text_from_csv(file_bytes, extension)
    else:
        # Image
        return extract_text_from_image(file_bytes, mime_type)
