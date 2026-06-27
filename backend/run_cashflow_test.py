"""
CreditBridge — Cashflow Layered Test Executor
Simulates connected AA feeds + manually uploaded business ledger statement sheets
for applicant 'karan' to test the revised Cashflow Agent.
Saves structured and human-readable results inside real_test/cashflow/ folder.

Run: venv\\Scripts\\python run_cashflow_test.py
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
logger = logging.getLogger("cashflow_test")

from database import get_db
from database_mongo import init_mongo, get_mongo_db, is_mongo_available, upsert_aa_feed
from data.cashflow_seeds import get_transactions_by_phone
from coded_tools.creditbridge.cashflow_tool import CashflowScoringTool


def ensure_karan_exists():
    with get_db() as conn:
        row = conn.execute("SELECT id FROM applicants WHERE id = ?", ("karan",)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO applicants (id, name, phone_encrypted, email_encrypted, aadhaar_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                ("karan", "Karan Mehta", "ENC:phone", "ENC:karan@gmail.com", "HASH:aadhaar")
            )
            conn.commit()


async def run_test():
    ensure_karan_exists()
    
    # 1. Initialize MongoDB Atlas
    ok = await init_mongo()
    if not ok:
        logger.error("Failed to connect to MongoDB Atlas.")
        return

    db = get_mongo_db()

    # Clear previous cashflow test data for karan
    await db.account_aggregators.delete_many({"applicant_id": "karan"})
    await db.bank_statements.delete_many({"applicant_id": "karan"})
    logger.info("Cleared previous cashflow test data.")

    # 2. Simulate AA Consent Feed (Ravi Kumar: 9876543210 - Salaried)
    logger.info("\n[1/3] Simulating Account Aggregator digital link (Phone: 9876543210)...")
    aa_txs = get_transactions_by_phone("9876543210")
    await upsert_aa_feed(
        applicant_id="karan",
        phone_number="9876543210",
        bank_name="HDFC Bank",
        transactions=aa_txs
    )
    logger.info(f"AA Connected: Loaded {len(aa_txs)} transactions with 100% trust level.")

    # 3. Simulate uploading a handwritten business ledger (self_reported)
    logger.info("\n[2/3] Simulating uploading manual offline business ledger...")
    ledger_text = """
    DAILY SALES CASH LEDGER - KARAN FRUIT STALL
    Date: 2024-02-15
    Income / Cash Sales: Rs. 14,500 (Credit)
    Income / Cash Sales: Rs. 12,000 (Credit)
    Expenses / Transport: Rs. 3,500 (Debit)
    Expenses / Fruit purchase: Rs. 18,000 (Debit)
    Status: Verified by Self
    """
    ledger_txs = [
        {"date": "2024-02-15", "amount": 14500, "type": "credit", "description": "Fruit Stall Daily Cash Sale"},
        {"date": "2024-02-15", "amount": 12000, "type": "credit", "description": "Fruit Stall Daily Cash Sale"},
        {"date": "2024-02-15", "amount": 3500, "type": "debit", "description": "Fruit Stall Transport Exp"},
        {"date": "2024-02-15", "amount": 18000, "type": "debit", "description": "Fruit Stall Purchase Veg/Fruit"},
    ]

    # Insert into bank_statements collection
    file_bytes = ledger_text.encode("utf-8")
    file_hash = "sha256:" + hashlib.sha256(file_bytes).hexdigest()
    
    await db.bank_statements.insert_one({
        "applicant_id": "karan",
        "original_filename": "fruit_stall_feb_ledger.txt",
        "file_hash": file_hash,
        "file_bytes_b64": base64.b64encode(file_bytes).decode(),
        "mime_type": "text/plain",
        "file_size_bytes": len(file_bytes),
        "stage": "scored",
        "verification_level": "self_reported",  # 40% trust level
        "transactions": ledger_txs,
        "upload_timestamp": datetime.now(timezone.utc),
    })
    logger.info(f"Uploaded statement: Ledger parsed successfully, {len(ledger_txs)} transactions saved (40% trust level).")

    # 4. Invoke Cashflow Scoring Tool
    logger.info("\n[3/3] Running CashflowScoringTool for 'karan'...")
    tool = CashflowScoringTool()
    tool_result = await tool.async_invoke(
        args={"applicant_id": "karan"},
        sly_data={}
    )

    # 5. Output scoring summary to console
    print("\n" + "=" * 65)
    print("  LAYERED CASHFLOW ASSESSMENT SUMMARY")
    print("=" * 65)
    print(f"Applicant ID : {tool_result.get('applicant_id')}")
    print(f"Final Score  : {tool_result.get('final_cashflow_score')}/100")
    print(f"Reason       : {tool_result.get('reason')}")
    print(f"Status       : {tool_result.get('status')}")
    
    metrics = tool_result.get("metrics", {})
    print(f"\nCalculated metrics:")
    print(f"  - Avg Monthly Balance    : INR {metrics.get('average_monthly_balance')}")
    print(f"  - Monthly Credits        : INR {metrics.get('monthly_credits')}")
    print(f"  - Weighted Credits       : INR {metrics.get('monthly_weighted_credits')}")
    print(f"  - Transaction Bounces    : {metrics.get('bounced_transactions_count')}")
    print(f"  - Total Transactions     : {metrics.get('transaction_count')}")

    matrix = tool_result.get("trust_matrix", {})
    print(f"\nTrust Verification Matrix:")
    print(f"  - Account Aggregator (AA): {matrix.get('account_aggregator_pct')}%")
    print(f"  - Document PDF Uploads   : {matrix.get('document_uploaded_pct')}%")
    print(f"  - Self-Reported Ledgers  : {matrix.get('self_reported_pct')}%")
    print(f"  - Summary Description    : {matrix.get('trust_description')}")
    print("=" * 65)

    # 6. Save results to backend/real_test/cashflow/
    target_dir = os.path.abspath(os.path.join(_this_dir, "real_test", "cashflow"))
    os.makedirs(target_dir, exist_ok=True)
    
    results_path = os.path.join(target_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(tool_result, f, indent=2)
    logger.info(f"JSON results saved to: {results_path}")

    report_path = os.path.join(target_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Layered Cashflow Agent Test Report\n\n")
        f.write(f"**Executed at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**Applicant:** Karan Mehta (`karan`)\n")
        f.write(f"**Final Cashflow Score:** **{tool_result.get('final_cashflow_score')}/100**\n")
        f.write(f"**Status:** {tool_result.get('status')}\n\n")
        f.write(f"## Summary Assessment\n> {tool_result.get('reason')}\n\n")
        
        f.write(f"## Cashflow Metrics\n")
        f.write(f"- **Average Monthly Balance:** INR {metrics.get('average_monthly_balance'):,}\n")
        f.write(f"- **Monthly Credits (Deposits):** INR {metrics.get('monthly_credits'):,}\n")
        f.write(f"- **Weighted Monthly Credits:** INR {metrics.get('monthly_weighted_credits'):,}\n")
        f.write(f"- **Total Transaction Count:** {metrics.get('transaction_count')} rows\n")
        f.write(f"- **Bounced Transactions Count:** {metrics.get('bounced_transactions_count')}\n\n")

        f.write(f"## Verification Trust Matrix\n")
        f.write(f"| Verification Level | Percentage contribution | Trust Multiplier applied |\n")
        f.write(f"|---|---|---|\n")
        f.write(f"| **Account Aggregator (AA)** | {matrix.get('account_aggregator_pct')}% | 1.00x (Full credit) |\n")
        f.write(f"| **Bank PDF/CSV Uploads** | {matrix.get('document_uploaded_pct')}% | 0.85x (15% discount) |\n")
        f.write(f"| **Self-Reported Ledgers** | {matrix.get('self_reported_pct')}% | 0.40x (60% discount) |\n\n")
        f.write(f"**Audit Tag:** `{matrix.get('trust_description')}`\n\n")
        f.write(f"## Database Insertion Status\n")
        f.write(f"- **Collection `account_aggregators` entries:** 1 connected feed\n")
        f.write(f"- **Collection `bank_statements` entries:** 1 manual ledger statement document\n")

    logger.info(f"Markdown report saved to: {report_path}")


if __name__ == "__main__":
    import base64
    asyncio.run(run_test())
