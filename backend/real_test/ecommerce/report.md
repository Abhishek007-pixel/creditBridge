# E-commerce Refined Agent Test Report

- **Executed at:** 2026-06-27 18:05:51 UTC
- **Score (Ecommerce Tool):** 60/100
- **Reasoning:** 1 invoice(s) analyzed. Avg spent: ₹8,450. Prepaid ratio: 100%. Livelihood asset bonus of +15 points applied (income-generating investments detected).

## OCR & LLM Classifier Validation Tests
- **Sewing Machine Receipt (Allowed & Livelihood Asset):** `is_valid` = **True**, Livelihood Asset = **True** (Expected: True/True)
- **Swiggy Receipt Rejection:** `is_valid` = **False**, reason = `Food receipts/deliveries (Zomato, Swiggy, restaurants, etc.)` (Expected: False/Rejected)
- **Price < Rs. 150 Rejection:** `is_valid` = **False**, reason = `Total amount less than 150 INR` (Expected: False/Rejected)
