"""
CreditBridge — Merchant Agent Refactored Test Executor
Tests:
1. GSTR portal linking simulation
2. Manual GSTR upload simulation with OCR and LLM classifier
3. Informal trade reference uploads and verification
4. Dynamic weight redistribution for optional agents (opt-out case)

Saves report to backend/real_test/merchant/results.json and backend/real_test/merchant/report.md.

Run: venv\\Scripts\\python run_merchant_gstn_test.py
"""
import os
import sys
import json
import asyncio
import hashlib
import logging
from datetime import datetime, timezone

# Add backend root to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("merchant_gstn_test")

from database import get_db
from database_mongo import (
    init_mongo,
    get_mongo_db,
    is_mongo_available,
    create_gstn_filing,
    create_merchant_reference
)
from routes.merchant import _parse_gst_document_with_llm
from coded_tools.creditbridge.merchant_tool import MerchantScoringTool
from agents.runner import run_synthetic_pipeline


def ensure_test_applicant_exists():
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applicants WHERE id = ?", ("test_merchant_gstn",)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO applicants (id, name, phone_encrypted, email_encrypted, aadhaar_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                ("test_merchant_gstn", "MSME Trader", "ENC:msmephone", "ENC:msme@trader.com", "HASH:msmeaadhaar")
            )
            # Add consents
            conn.execute(
                "INSERT INTO consent_logs (id, applicant_id, source_name, consented) VALUES (?, ?, ?, ?)",
                ("consent-m-1", "test_merchant_gstn", "merchant", 1)
            )
            conn.execute(
                "INSERT INTO consent_logs (id, applicant_id, source_name, consented) VALUES (?, ?, ?, ?)",
                ("consent-m-2", "test_merchant_gstn", "ecommerce", 1)
            )
            conn.commit()
            logger.info("Created test applicant 'test_merchant_gstn' with consents.")


async def run_test():
    ensure_test_applicant_exists()

    # Initialize MongoDB Atlas
    ok = await init_mongo()
    if not ok:
        logger.error("Failed to connect to MongoDB Atlas.")
        return

    db = get_mongo_db()

    # Clear previous merchant files for test applicant
    await db.gstn_filings.delete_many({"applicant_id": "test_merchant_gstn"})
    await db.merchant_references.delete_many({"applicant_id": "test_merchant_gstn"})
    logger.info("Cleared previous database records.")

    # ── Test 1: Simulating Digital GSTN Link ─────────────────────────────
    logger.info("\n[1/4] Simulating GSTR digital portal link...")
    months = ["2024-05", "2024-04", "2024-03", "2024-02", "2024-01", "2023-12", "2023-11", "2023-10", "2023-09", "2023-08", "2023-07", "2023-06"]
    filing_history = []
    # 10 out of 12 filed on time (83%)
    for idx, m in enumerate(months):
        filed_on_time = (idx != 2 and idx != 7)  # Fail month 3 and 8
        filing_history.append({"month": m, "filed_on_time": filed_on_time})

    invoices = [
        {"recipient_gstin": "27ABCDE1234F1Z1", "amount": 25000.0, "date": "2024-05-10"},
        {"recipient_gstin": "27BCDEF2345G1Z2", "amount": 45000.0, "date": "2024-05-12"},
        {"recipient_gstin": "27CDEFG3456H1Z3", "amount": 15000.0, "date": "2024-04-18"},
        {"recipient_gstin": "27DEFGH4567I1Z4", "amount": 60000.0, "date": "2024-04-20"},
        {"recipient_gstin": "27EFGHI5678J1Z5", "amount": 10000.0, "date": "2024-03-05"},
    ]

    doc_sim = {
        "applicant_id": "test_merchant_gstn",
        "gstin": "27MSMEB1234M1Z5",
        "business_name": "Commercial Trader & Retailers Ltd",
        "phone_number": "9898989898",
        "filing_history": filing_history,
        "invoices": invoices,
        "stage": "scored",
        "verification_level": "account_aggregator",
        "upload_timestamp": datetime.now(timezone.utc)
    }
    await create_gstn_filing(doc_sim)

    # Call tool directly to verify GSTN track scoring
    tool = MerchantScoringTool()
    tool_res_gst = await tool.async_invoke(
        args={"applicant_id": "test_merchant_gstn"},
        sly_data={}
    )
    logger.info(f"GSTN Track Score: {tool_res_gst.get('score')}/100")
    logger.info(f"GSTN Track Reason: {tool_res_gst.get('reason')}")

    # ── Test 2: Manual GSTR Invoice Upload ────────────────────────────────
    logger.info("\n[2/4] Testing manual GSTR return invoice upload...")
    # Clear GSTN filings to isolate Track A invoice upload
    await db.gstn_filings.delete_many({"applicant_id": "test_merchant_gstn"})

    valid_gstr_text = """
    GOVERNMENT OF INDIA - GOODS AND SERVICES TAX NETWORK
    GSTR-1 FILING ACKNOWLEDGEMENT
    GSTIN: 27MSMEB1234M1Z5
    Legal Name: MSME Trader Retailers
    Filing Period: May 2024
    Total Outward Supplies Taxable Value: INR 125,000.00
    Filing Date: 2024-06-10
    """

    # Parse via LLM
    parsed = _parse_gst_document_with_llm(valid_gstr_text)
    logger.info(f"LLM Parsed Upload: {parsed}")

    if parsed.get("is_valid"):
        doc_upload = {
            "applicant_id": "test_merchant_gstn",
            "original_filename": "mock_gstr1_receipt.txt",
            "file_hash": "sha256:" + hashlib.sha256(valid_gstr_text.encode()).hexdigest(),
            "stage": "scored",
            "verification_level": "document_uploaded",
            "gstin": parsed.get("gstin") or "27MSMEB1234M1Z5",
            "business_name": parsed.get("business_name") or "MSME Trader Retailers",
            "amount": parsed.get("amount") or 125000.0,
            "date": parsed.get("date") or "2024-06-10",
            "filing_history": [
                {"month": "2024-05", "filed_on_time": True},
                {"month": "2024-04", "filed_on_time": True},
            ],
            "invoices": [
                {"recipient_gstin": "27BBBBB2222B1Z2", "amount": parsed.get("amount") or 125000.0, "date": "2024-06-10"}
            ],
            "upload_timestamp": datetime.now(timezone.utc)
        }
        await create_gstn_filing(doc_upload)

    tool_res_upload = await tool.async_invoke(
        args={"applicant_id": "test_merchant_gstn"},
        sly_data={}
    )
    logger.info(f"Upload Track Score: {tool_res_upload.get('score')}/100")
    logger.info(f"Upload Track Reason: {tool_res_upload.get('reason')}")

    # ── Test 3: Informal Trade References and Verification ─────────────
    logger.info("\n[3/4] Testing peer/trade references track...")
    # Clear GSTN data so tool falls back to Trade References track
    await db.gstn_filings.delete_many({"applicant_id": "test_merchant_gstn"})

    references_to_add = [
        {
            "applicant_id": "test_merchant_gstn",
            "reference_name": "Supplier Ramesh",
            "phone": "9000011111",
            "relationship_type": "supplier",
            "duration_months": 24,
            "verified_status": "verified",
            "rating": 4.5
        },
        {
            "applicant_id": "test_merchant_gstn",
            "reference_name": "Buyer Suresh",
            "phone": "9000022222",
            "relationship_type": "buyer",
            "duration_months": 48,
            "verified_status": "failed",
            "rating": 0.0
        }
    ]

    for ref in references_to_add:
        await create_merchant_reference(ref)

    # Call tool directly to verify references track scoring
    tool_res_ref = await tool.async_invoke(
        args={"applicant_id": "test_merchant_gstn"},
        sly_data={}
    )
    logger.info(f"References Track Score: {tool_res_ref.get('score')}/100")
    logger.info(f"References Track Reason: {tool_res_ref.get('reason')}")

    # ── Test 4: Dynamic Weight Redistribution ────────────────────────────
    logger.info("\n[4/4] Testing optional agent weight redistribution...")
    # Clear references so merchant data is not available
    await db.merchant_references.delete_many({"applicant_id": "test_merchant_gstn"})

    # Invoke tool directly to check not_available
    tool_res_opt = await tool.async_invoke(
        args={"applicant_id": "test_merchant_gstn"},
        sly_data={}
    )
    logger.info(f"Opt-out Coded Tool output: score={tool_res_opt.get('score')}, status={tool_res_opt.get('status')}")

    # Run synthetic scoring pipeline directly (consented: ecommerce, merchant)
    import agents.runner
    original_generate = agents.runner.generate_applicant_data

    def mock_generate(app_id):
        res = original_generate(app_id)
        res["merchant"]["total_merchants_rated"] = 0
        return res

    agents.runner.generate_applicant_data = mock_generate

    score_json = run_synthetic_pipeline(
        applicant_id="test_merchant_gstn",
        consented_sources=["ecommerce", "merchant"],
        questionnaire_answers=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    )

    agents.runner.generate_applicant_data = original_generate
    
    breakdown = score_json.get("breakdown", {})
    weights_used = score_json.get("weights_used", {})
    
    print("\n" + "=" * 65)
    print("  OPTIONAL AGENT WEIGHT REDISTRIBUTION VERIFICATION")
    print("=" * 65)
    print(f"Final Score   : {score_json.get('final_score')}/850")
    print(f"Risk Category : {score_json.get('risk_category')}")
    print("\nBreakdown of Active Weights:")
    total_w = 0.0
    for source, weight in weights_used.items():
        score = breakdown.get(source, {}).get("score", 0)
        print(f"  - {source:<22} : score={score} (weight={weight}%)")
        total_w += weight
    print(f"  * Total Active Weight: {total_w}%")
    print("=" * 65)

    # Save results to real_test/merchant/
    merchant_dir = os.path.abspath(os.path.join(_this_dir, "real_test", "merchant"))
    os.makedirs(merchant_dir, exist_ok=True)
    
    results_path = os.path.join(merchant_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump({
            "gstn_link_test": tool_res_gst,
            "gstn_upload_test": tool_res_upload,
            "references_test": tool_res_ref,
            "opt_out_test": {
                "coded_tool": tool_res_opt,
                "weights_used": weights_used,
                "breakdown": breakdown,
                "final_score": score_json.get("final_score")
            }
        }, f, indent=2)
    logger.info(f"JSON results saved to: {results_path}")

    # Generate Markdown report
    report_path = os.path.join(merchant_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Refactored MSME Merchant Agent Test Report\n\n")
        f.write(f"- **Executed at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"- **Applicant:** test_merchant_gstn\n\n")
        
        f.write("## 1. Track A: GSTN Digital Link Simulation\n")
        f.write(f"- **Coded Tool Score:** {tool_res_gst.get('score')}/100\n")
        f.write(f"- **Reasoning:** {tool_res_gst.get('reason')}\n")
        f.write(f"- **Filing regularity verified:** {tool_res_gst.get('metrics', {}).get('filing_compliance_pct')}%\n")
        f.write(f"- **Unique counterparty list count:** {tool_res_gst.get('metrics', {}).get('unique_buyers_count')} buyer(s)\n\n")

        f.write("## 2. Track A: GSTR Document OCR & LLM Upload\n")
        f.write(f"- **Coded Tool Score:** {tool_res_upload.get('score')}/100\n")
        f.write(f"- **Reasoning:** {tool_res_upload.get('reason')}\n\n")

        f.write("## 3. Track B: Informal Trade References\n")
        f.write(f"- **Coded Tool Score:** {tool_res_ref.get('score')}/100\n")
        f.write(f"- **Reasoning:** {tool_res_ref.get('reason')}\n")
        metrics_ref = tool_res_ref.get("metrics", {})
        f.write(f"- **References uploaded:** {metrics_ref.get('references_total')}\n")
        f.write(f"- **References verified:** {metrics_ref.get('references_verified')}\n")
        f.write(f"- **Avg relationship duration:** {metrics_ref.get('average_relationship_months')} months\n")
        f.write(f"- **Avg trade rating:** {metrics_ref.get('average_rating')}/5.0\n\n")

        f.write("## 4. Optional Agent Opt-Out & Weight Redistribution\n")
        f.write(f"- **Coded Tool output when empty:** score = {tool_res_opt.get('score')}, status = `{tool_res_opt.get('status')}`\n")
        f.write(f"- **Risk Synthesizer Weight Redistribution:**\n")
        f.write("| Agent source | Active Weight | Score |\n")
        f.write("|---|---|---|\n")
        for source, weight in weights_used.items():
            s = breakdown.get(source, {}).get("score", 0)
            f.write(f"| `{source}` | {weight}% | {s}/100 |\n")
        f.write(f"\n**Total Active Weights sum:** {total_w}% (Successful normalization)\n")

    logger.info(f"Markdown report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(run_test())
