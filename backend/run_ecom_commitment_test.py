"""
CreditBridge — Ecommerce & Financial Commitment Test Executor
Tests real document processing, classification rejections, livelihood asset bonuses,
and savings commitment consistency/diversity scoring.
Saves verification logs under real_test/ecommerce/ and real_test/commitments/ folders.

Run: venv\\Scripts\\python run_ecom_commitment_test.py
"""
import os
import sys
import json
import asyncio
import hashlib
import logging
import base64
from datetime import datetime, timezone

# Add backend root to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ecom_commitment_test")

from database import get_db
from database_mongo import init_mongo, get_mongo_db, is_mongo_available
from routes.ecommerce import _parse_invoice_with_llm
from routes.commitments import _parse_commitment_with_llm
from coded_tools.creditbridge.ecommerce_tool import EcommerceScoringTool
from coded_tools.creditbridge.financial_commitment_tool import FinancialCommitmentScoringTool
from agents.runner import run_synthetic_pipeline


def ensure_test_applicant_exists():
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applicants WHERE id = ?", ("test_ecom_commit",)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO applicants (id, name, phone_encrypted, email_encrypted, aadhaar_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                ("test_ecom_commit", "Test Applicant", "ENC:testphone", "ENC:test@creditbridge.com", "HASH:testaadhaar")
            )
            # Consent for both ecommerce and financial commitment
            conn.execute(
                "INSERT INTO consent_logs (id, applicant_id, source_name, consented) VALUES (?, ?, ?, ?)",
                ("consent-ecom-1", "test_ecom_commit", "ecommerce", 1)
            )
            conn.execute(
                "INSERT INTO consent_logs (id, applicant_id, source_name, consented) VALUES (?, ?, ?, ?)",
                ("consent-commit-1", "test_ecom_commit", "financial_commitment", 1)
            )
            conn.commit()
            logger.info("Created test applicant 'test_ecom_commit' with consents.")


async def run_test():
    ensure_test_applicant_exists()

    # 1. Initialize MongoDB Atlas
    ok = await init_mongo()
    if not ok:
        logger.error("Failed to connect to MongoDB Atlas.")
        return

    db = get_mongo_db()

    # Clear previous test data for this applicant
    await db.ecommerce_invoices.delete_many({"applicant_id": "test_ecom_commit"})
    await db.financial_commitments.delete_many({"applicant_id": "test_ecom_commit"})
    logger.info("Cleared previous test database records.")

    # 2. Test LLM Parser Rejections (Offline prompt verification)
    logger.info("\n[1/5] Testing LLM Invoice Parser Classifiers and Rejections...")
    
    # Valid Sewing Machine Text
    valid_ecom_text = """
    AMAZON RETAIL INDIA INVOICE
    Order Date: 2024-05-10
    Sold to: Test Applicant
    Item: USHA JANOME SEWING MACHINE WITH MOTOR
    Quantity: 1
    Total Amount Paid: INR 8,450.00
    Payment Method: UPI Prepaid
    """
    
    # Invalid Food Order Text
    invalid_food_text = """
    SWIGGY ORDER RECEIPT
    Date: 2024-06-25
    Restaurant: Biryani House
    Items Ordered:
      - Special Chicken Biryani x2 (Rs 260)
      - Coca-Cola x2 (Rs 80)
    Total Paid: Rs 340.00
    Payment: Cash on Delivery
    """
    
    # Invalid Low Amount Text
    low_amount_text = """
    FLIPKART BILL
    Date: 2024-04-15
    Item: Phone Case Cover
    Total Paid: Rs 120.00
    Payment: Prepaid
    """

    # Invalid non-savings document
    invalid_commitment_text = """
    BSNL TELEPHONE BILL
    Billing Cycle: May 2024
    Total Amount Due: Rs 450.00
    Payment Status: Paid
    """

    logger.info("Validating valid e-commerce sewing machine receipt via LLM classifier:")
    parsed_ecom = _parse_invoice_with_llm(valid_ecom_text)
    logger.info(f"  Parsed output: is_valid={parsed_ecom.get('is_valid')}, platform={parsed_ecom.get('platform')}, is_livelihood_asset={parsed_ecom.get('is_livelihood_asset')}, amount={parsed_ecom.get('amount')}")

    logger.info("Validating Swiggy receipt (should be rejected):")
    parsed_food = _parse_invoice_with_llm(invalid_food_text)
    logger.info(f"  Parsed output: is_valid={parsed_food.get('is_valid')}, reason={parsed_food.get('rejection_reason')}")

    logger.info("Validating low amount receipt < Rs 150 (should be rejected):")
    parsed_low = _parse_invoice_with_llm(low_amount_text)
    logger.info(f"  Parsed output: is_valid={parsed_low.get('is_valid')}, reason={parsed_low.get('rejection_reason')}")

    logger.info("Validating non-savings utility bill under commitments parser (should be rejected):")
    parsed_commitment_rej = _parse_commitment_with_llm(invalid_commitment_text)
    logger.info(f"  Parsed output: is_valid={parsed_commitment_rej.get('is_valid')}, reason={parsed_commitment_rej.get('rejection_reason')}")

    # 3. Simulate process invoice uploads into MongoDB Atlas
    logger.info("\n[2/5] Seeding valid e-commerce & savings commitment records into MongoDB...")
    
    # Seed 1: E-commerce Sewing Machine Purchase (with Livelihood Asset Flag)
    file_bytes_1 = valid_ecom_text.encode("utf-8")
    await db.ecommerce_invoices.insert_one({
        "applicant_id": "test_ecom_commit",
        "original_filename": "amazon_sewing_machine_invoice.txt",
        "file_hash": "sha256:" + hashlib.sha256(file_bytes_1).hexdigest(),
        "file_bytes_b64": base64.b64encode(file_bytes_1).decode(),
        "mime_type": "text/plain",
        "file_size_bytes": len(file_bytes_1),
        "stage": "scored",
        "platform": parsed_ecom.get("platform") or "Amazon",
        "amount": float(parsed_ecom.get("amount") or 8450.00),
        "payment_method": parsed_ecom.get("payment_method") or "Prepaid",
        "date": parsed_ecom.get("date") or "2024-05-10",
        "item_description": parsed_ecom.get("item_description") or "Usha Sewing Machine",
        "is_livelihood_asset": parsed_ecom.get("is_livelihood_asset") if parsed_ecom.get("is_livelihood_asset") is not None else True,
        "upload_timestamp": datetime.now(timezone.utc),
    })

    # Seed 2: Commitments - LIC Premium Payment (Insurance)
    lic_text = "LIC OF INDIA PREMIUM RECEIPT. Policy: 123456789. Premium Paid: Rs. 3,500. Date: 2024-06-01. Period: Monthly."
    file_bytes_lic = lic_text.encode("utf-8")
    await db.financial_commitments.insert_one({
        "applicant_id": "test_ecom_commit",
        "original_filename": "lic_premium_jun.txt",
        "file_hash": "sha256:" + hashlib.sha256(file_bytes_lic).hexdigest(),
        "file_bytes_b64": base64.b64encode(file_bytes_lic).decode(),
        "mime_type": "text/plain",
        "file_size_bytes": len(file_bytes_lic),
        "stage": "scored",
        "provider": "LIC India",
        "amount": 3500.00,
        "payment_date": "2024-06-01",
        "policy_type": "insurance",
        "period": "Monthly",
        "upload_timestamp": datetime.now(timezone.utc),
    })

    # Seed 3: Commitments - HDFC Mutual Fund SIP (SIP)
    sip_text = "HDFC MUTUAL FUND SIP TRANSACTIONS. Fund: HDFC Top 100. Amount: Rs. 2,000. Date: 2024-06-15."
    file_bytes_sip = sip_text.encode("utf-8")
    await db.financial_commitments.insert_one({
        "applicant_id": "test_ecom_commit",
        "original_filename": "hdfc_sip_jun.txt",
        "file_hash": "sha256:" + hashlib.sha256(file_bytes_sip).hexdigest(),
        "file_bytes_b64": base64.b64encode(file_bytes_sip).decode(),
        "mime_type": "text/plain",
        "file_size_bytes": len(file_bytes_sip),
        "stage": "scored",
        "provider": "HDFC Mutual Fund",
        "amount": 2000.00,
        "payment_date": "2024-06-15",
        "policy_type": "sip",
        "period": "Monthly",
        "upload_timestamp": datetime.now(timezone.utc),
    })
    logger.info("Successfully seeded database records.")

    # 4. Invoke Coded Tools Directly
    logger.info("\n[3/5] Invoking Ecommerce & Financial Commitment Coded Tools...")
    
    ecom_tool = EcommerceScoringTool()
    ecom_res = await ecom_tool.async_invoke(
        args={"applicant_id": "test_ecom_commit"},
        sly_data={}
    )
    logger.info(f"Ecommerce tool score: {ecom_res.get('score')}/100")
    logger.info(f"Ecommerce tool reason: {ecom_res.get('reason')}")

    commit_tool = FinancialCommitmentScoringTool()
    commit_res = await commit_tool.async_invoke(
        args={"applicant_id": "test_ecom_commit"},
        sly_data={}
    )
    logger.info(f"Commitment tool score: {commit_res.get('score')}/100")
    logger.info(f"Commitment tool reason: {commit_res.get('reason')}")

    # 5. Run Consolidated Synthetic Pipeline
    logger.info("\n[4/5] Running Consolidated Synthetic Pipeline...")
    pipeline_res = run_synthetic_pipeline(
        applicant_id="test_ecom_commit",
        consented_sources=["ecommerce", "financial_commitment"],
        questionnaire_answers=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    )
    
    print("\n" + "=" * 65)
    print("  ASSESSMENT RESULTS FOR TEST APPLICANT")
    print("=" * 65)
    print(f"Final score    : {pipeline_res.get('final_score')}/850")
    print(f"Risk Category  : {pipeline_res.get('risk_category')}")
    print(f"Decision       : {pipeline_res.get('decision')}")
    print(f"Loan Recommended: Rs. {pipeline_res.get('loan_recommended'):,}")
    print(f"Interest Rate  : {pipeline_res.get('interest_rate')}%")
    print("\nBreakdown of agent scores:")
    breakdown = pipeline_res.get("breakdown", {})
    for source, data in breakdown.items():
        print(f"  - {source:<22} : score={data.get('score')} (weight={data.get('weight_used')}%)")
    print("=" * 65)

    # 6. Save results to target verification directories
    logger.info("\n[5/5] Saving test logs and report outputs...")
    
    ecom_dir = os.path.abspath(os.path.join(_this_dir, "real_test", "ecommerce"))
    commit_dir = os.path.abspath(os.path.join(_this_dir, "real_test", "commitments"))
    os.makedirs(ecom_dir, exist_ok=True)
    os.makedirs(commit_dir, exist_ok=True)

    # Ecommerce JSON result
    with open(os.path.join(ecom_dir, "results.json"), "w") as f:
        json.dump({
            "parser_test": {
                "valid_receipt": parsed_ecom,
                "invalid_food": parsed_food,
                "invalid_low_amt": parsed_low
            },
            "tool_result": ecom_res,
            "pipeline_result": pipeline_res
        }, f, indent=2)
    logger.info(f"Saved e-commerce verification results to: {os.path.join(ecom_dir, 'results.json')}")

    # Commitments JSON result
    with open(os.path.join(commit_dir, "results.json"), "w") as f:
        json.dump({
            "parser_test": {
                "invalid_bill_rejection": parsed_commitment_rej
            },
            "tool_result": commit_res,
            "pipeline_result": pipeline_res
        }, f, indent=2)
    logger.info(f"Saved financial commitments verification results to: {os.path.join(commit_dir, 'results.json')}")

    # Generate visual markdown reports
    with open(os.path.join(ecom_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("# E-commerce Refined Agent Test Report\n\n")
        f.write(f"- **Executed at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"- **Score (Ecommerce Tool):** {ecom_res.get('score')}/100\n")
        f.write(f"- **Reasoning:** {ecom_res.get('reason')}\n\n")
        f.write("## OCR & LLM Classifier Validation Tests\n")
        f.write(f"- **Sewing Machine Receipt (Allowed & Livelihood Asset):** `is_valid` = **{parsed_ecom.get('is_valid')}**, Livelihood Asset = **{parsed_ecom.get('is_livelihood_asset')}** (Expected: True/True)\n")
        f.write(f"- **Swiggy Receipt Rejection:** `is_valid` = **{parsed_food.get('is_valid')}**, reason = `{parsed_food.get('rejection_reason')}` (Expected: False/Rejected)\n")
        f.write(f"- **Price < Rs. 150 Rejection:** `is_valid` = **{parsed_low.get('is_valid')}**, reason = `{parsed_low.get('rejection_reason')}` (Expected: False/Rejected)\n")

    with open(os.path.join(commit_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("# Financial Commitment New Agent Test Report\n\n")
        f.write(f"- **Executed at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"- **Score (Commitment Tool):** {commit_res.get('score')}/100\n")
        f.write(f"- **Reasoning:** {commit_res.get('reason')}\n\n")
        f.write("## Plan Diversity & Consistency Assessment\n")
        metrics = commit_res.get("metrics", {})
        f.write(f"- **Active Commitments Count:** {metrics.get('document_count')}\n")
        f.write(f"- **Average premium commitment amount:** INR {metrics.get('avg_amount'):,}\n")
        f.write(f"- **Consecutive monthly savings count:** {metrics.get('unique_months')} months\n")
        f.write(f"- **Product mix detected:** {', '.join(metrics.get('diversity_types', []))} (Score reflects diversity bonus)\n")

    logger.info("All verification reports compiled successfully.")


if __name__ == "__main__":
    asyncio.run(run_test())
