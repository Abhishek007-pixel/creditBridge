# Layered Cashflow Agent Test Report

**Executed at:** 2026-06-27 17:09:46 UTC
**Applicant:** Karan Mehta (`karan`)
**Final Cashflow Score:** **100/100**
**Status:** success

## Summary Assessment
> Monthly credits ₹49,417 (weighted: ₹46,767). Avg balance ₹27,542. Trust matrix: 88.8% AA + 11.2% Manual ledger. No transaction bounces detected.

## Cashflow Metrics
- **Average Monthly Balance:** INR 27,542.0
- **Monthly Credits (Deposits):** INR 49,417.0
- **Weighted Monthly Credits:** INR 46,767.0
- **Total Transaction Count:** 28 rows
- **Bounced Transactions Count:** 0

## Verification Trust Matrix
| Verification Level | Percentage contribution | Trust Multiplier applied |
|---|---|---|
| **Account Aggregator (AA)** | 88.8% | 1.00x (Full credit) |
| **Bank PDF/CSV Uploads** | 0.0% | 0.85x (15% discount) |
| **Self-Reported Ledgers** | 11.2% | 0.40x (60% discount) |

**Audit Tag:** `Verified: 88.8% AA, 0.0% Doc Uploads, 11.2% Ledgers`

## Database Insertion Status
- **Collection `account_aggregators` entries:** 1 connected feed
- **Collection `bank_statements` entries:** 1 manual ledger statement document
