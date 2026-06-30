# Refactored MSME Merchant Agent Test Report

- **Executed at:** 2026-06-27 18:26:26 UTC
- **Applicant:** test_merchant_gstn

## 1. Track A: GSTN Digital Link Simulation
- **Coded Tool Score:** 73.33333333333334/100
- **Reasoning:** GSTN verified (Commercial Trader & Retailers Ltd / 27MSMEB1234M1Z5): filed 10/12 returns on time. Active with 5 buyer(s). Total verified turnover ₹155,000.
- **Filing regularity verified:** 83%
- **Unique counterparty list count:** 5 buyer(s)

## 2. Track A: GSTR Document OCR & LLM Upload
- **Coded Tool Score:** 66.0/100
- **Reasoning:** GSTN verified (MSME Trader Retailers / 27MSMEB1234M1Z5): filed 2/2 returns on time. Active with 1 buyer(s). Total verified turnover ₹125,000.

## 3. Track B: Informal Trade References
- **Coded Tool Score:** 82.0/100
- **Reasoning:** Trade references: 1/2 verified. Avg relationship longevity: 36.0 months. Avg trade rating: 4.5/5.0.
- **References uploaded:** 2
- **References verified:** 1
- **Avg relationship duration:** 36.0 months
- **Avg trade rating:** 4.5/5.0

## 4. Optional Agent Opt-Out & Weight Redistribution
- **Coded Tool output when empty:** score = -1, status = `not_available`
- **Risk Synthesizer Weight Redistribution:**
| Agent source | Active Weight | Score |
|---|---|---|
| `psychometric` | 0.625% | 99/100 |
| `ecommerce` | 0.375% | 80/100 |

**Total Active Weights sum:** 1.0% (Successful normalization)
