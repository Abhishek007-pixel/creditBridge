"""
CreditBridge — Real Test Executor
Scans 'real_test/' folder for files, uploads and runs them through the 6-stage pipeline
for a test applicant 'karan' (creating the applicant in SQLite if needed),
verifies MongoDB Atlas updates, computes consistency scoring, and writes results back.

Run this script:
  venv\Scripts\python run_real_test.py
"""

import os
import sys
import json
import asyncio
import base64
import logging
import hashlib
from datetime import datetime, timezone

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("real_test")

from database import get_db
from database_mongo import init_mongo, get_mongo_db, is_mongo_available
from routes.bills import _process_bill, ALLOWED_EXTENSIONS
from coded_tools.creditbridge.bill_consistency_tool import BillConsistencyScoringTool


def ensure_karan_exists():
    """Ensure a test applicant with ID 'karan' exists in SQLite database."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applicants WHERE id = ?", ("karan",)).fetchone()
        if not row:
            logger.info("Creating test applicant 'karan' in SQLite database...")
            # Using placeholder values for encrypted fields
            conn.execute(
                "INSERT INTO applicants (id, name, phone_encrypted, email_encrypted, aadhaar_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                ("karan", "Karan Mehta", "ENC:phone_placeholder", "ENC:karan@gmail.com", "HASH:aadhaar_placeholder")
            )
            conn.commit()
            logger.info("Test applicant 'karan' created.")
        else:
            logger.info("Test applicant 'karan' already exists in SQLite.")


async def process_files():
    # 1. Initialize DBs
    ensure_karan_exists()
    mongo_ok = await init_mongo()
    if not mongo_ok:
        logger.error("MongoDB Atlas connection failed! Cannot proceed with real test.")
        return

    # 2. Check for files in real_test directory
    real_test_dir = os.path.abspath(os.path.join(_this_dir, "real_test"))
    if not os.path.exists(real_test_dir):
        logger.error(f"Directory {real_test_dir} does not exist.")
        return

    files = [f for f in os.listdir(real_test_dir) if os.path.isfile(os.path.join(real_test_dir, f))]
    # Filter files by extensions
    valid_files = []
    for f in files:
        ext = "." + f.rsplit(".", 1)[-1].lower() if "." in f else ""
        if ext in ALLOWED_EXTENSIONS:
            valid_files.append((f, ext))

    if not valid_files:
        logger.warning("=" * 70)
        logger.warning(" NO TEST FILES FOUND IN 'real_test/' DIRECTORY!")
        logger.warning(" Please drop some files inside the 'real_test' folder.")
        logger.warning(" Example files:")
        logger.warning("   - rent_receipt_jan.pdf / rent_receipt_feb.jpg")
        logger.warning("   - electricity_bill.pdf")
        logger.warning("   - phone_bill.png")
        logger.warning("=" * 70)
        return

    logger.info(f"Found {len(valid_files)} valid test file(s) in 'real_test/':")
    for vf, ext in valid_files:
        logger.info(f"  - {vf} (Type: {ext})")

    # Clean existing documents in MongoDB for 'karan' to start clean (optional, but good for repeatable tests)
    db = get_mongo_db()
    deleted_docs = await db.bill_documents.delete_many({"applicant_id": "karan"})
    deleted_streams = await db.bill_streams.delete_many({"applicant_id": "karan"})
    logger.info(f"Cleared previous test data: deleted {deleted_docs.deleted_count} docs and {deleted_streams.deleted_count} streams.")

    # 3. Process each file
    processed_doc_ids = []
    for idx, (filename, ext) in enumerate(valid_files):
        filepath = os.path.join(real_test_dir, filename)
        logger.info(f"\n[{idx+1}/{len(valid_files)}] Processing file: {filename} ...")
        
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        # Map extension to MIME type
        mime_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")
        file_hash = "sha256:" + hashlib.sha256(file_bytes).hexdigest()

        # Create the uploaded doc record in MongoDB
        file_b64 = base64.b64encode(file_bytes).decode()
        doc_id = await db.bill_documents.insert_one({
            "applicant_id": "karan",
            "original_filename": filename,
            "file_hash": file_hash,
            "file_bytes_b64": file_b64,
            "mime_type": mime_type,
            "file_size_bytes": len(file_bytes),
            "stage": "uploaded",
            "upload_timestamp": datetime.now(timezone.utc),
            "verification_level": "image_uploaded" if mime_type.startswith("image/") else "document_uploaded",
            "flags": [],
            "classification": None,
            "extraction": None,
            "stream_score": None,
            "reason": None,
        })
        doc_id_str = str(doc_id.inserted_id)
        processed_doc_ids.append(doc_id_str)
        logger.info(f"Inserted document record in MongoDB bill_documents with ID: {doc_id_str}")

        # Run pipeline process function
        await _process_bill(
            doc_id=doc_id_str,
            file_bytes=file_bytes,
            mime_type=mime_type,
            applicant_id="karan",
            original_ext=ext
        )

    # 4. Run the Coded Tool to score the applicant's streams
    logger.info("\n=== RUNNING BILL CONSISTENCY SCORING TOOL ===")
    tool = BillConsistencyScoringTool()
    tool_result = await tool.async_invoke(
        args={"applicant_id": "karan"},
        sly_data={}
    )
    
    # Beautify result
    print("\n" + "=" * 60)
    print("  SCORING RESULT SUMMARY")
    print("=" * 60)
    print(f"Applicant ID : {tool_result.get('applicant_id')}")
    print(f"Final Score  : {tool_result.get('final_bill_score')}/100")
    print(f"Reason       : {tool_result.get('reason')}")
    print(f"Bills Count  : {tool_result.get('bills_uploaded')}")
    print(f"Status       : {tool_result.get('status')}")
    
    streams = tool_result.get("streams", [])
    print(f"\nStreams Found: {len(streams)}")
    for s in streams:
        print(f"\n  - Bill Type    : {s.get('bill_type')}")
        print(f"    Payee Name   : {s.get('payee_name')}")
        print(f"    Months       : {s.get('months_covered')}")
        print(f"    Avg Amount   : INR {s.get('avg_amount')}")
        print(f"    Stream Score : {s.get('stream_score')}/100")
        print(f"    Detail       : {s.get('reason')}")
    print("=" * 60)

    # 5. Save results to real_test folder
    results_path = os.path.join(real_test_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(tool_result, f, indent=2)
    logger.info(f"Scoring results saved to {results_path}")

    # Generate Markdown report
    report_path = os.path.join(real_test_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# CreditBridge Bill Agent Test Report\n\n")
        f.write(f"**Executed at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Applicant ID:** {tool_result.get('applicant_id')}\n")
        f.write(f"**Final Bill Score:** **{tool_result.get('final_bill_score')}/100**\n")
        f.write(f"**Status:** {tool_result.get('status')}\n\n")
        f.write(f"## Summary Reason\n> {tool_result.get('reason')}\n\n")
        f.write(f"## Processed Streams\n\n")
        
        if not streams:
            f.write("*No bill streams processed (synthetic fallback).* \n")
        else:
            for s in streams:
                f.write(f"### {s.get('bill_type').replace('_', ' ').title()} - {s.get('payee_name')}\n")
                f.write(f"- **Stream Score:** {s.get('stream_score')}/100\n")
                f.write(f"- **Months Covered:** {s.get('months_covered')}\n")
                f.write(f"- **Average Monthly Amount:** INR {s.get('avg_amount')}\n")
                f.write(f"- **Verification Level:** {s.get('verification_level')}\n")
                f.write(f"- **Details:** {s.get('reason')}\n\n")

        # Let's list documents currently in MongoDB Atlas
        f.write(f"## MongoDB Atlas Verification\n")
        f.write(f"- **Collection 'bill_documents' count:** {len(valid_files)} documents\n")
        f.write(f"- **Collection 'bill_streams' count:** {len(streams)} active streams\n")

    logger.info(f"Human-readable report saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(process_files())
