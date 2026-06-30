# Bill Agent — Planning POV

## 1. Why This Design is Stronger Than Phone Bill Agent

The original phone bill agent had one critical weakness: **it was a single-signal proxy for financial discipline**. A ₹300 Airtel bill is paid by almost everyone, including people who are genuinely high-risk. It's too easy, too universal, and too low-stakes to be a strong credit signal.

The new Bill Agent flips this by treating **consistency of financial obligation** as the core signal — not the type of bill. The key insight is:

> **The more you stand to lose by missing a payment, the more meaningful consistency is.**

- You don't stop paying **rent** because you lose your home.
- You don't stop paying **school fees** because your child gets expelled.
- You don't stop paying **EMIs** because your asset gets repossessed.

A street vendor paying ₹8,000 rent for 24 months is stronger evidence of creditworthiness than a salaried person who just got a credit card. **This is the core value proposition of alternative credit scoring** — and this agent captures it.

---

## 2. The Document Processing Pipeline

Here's how raw uploads should flow through the system:

```
User uploads file
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 1: VALIDATION GATE (reject before processing)│
│                                                     │
│  • File type: PDF, JPG, PNG, JPEG only              │
│  • File size: max 5MB per file, max 10 files total  │
│  • Filename / metadata quick scan                   │
│  • Reject: videos, executables, zip, Office docs    │
└──────────────────────────┬──────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 2: CONTENT EXTRACTION                        │
│                                                     │
│  Path A — PDF with embedded text                    │
│    → pdfplumber / PyMuPDF (fast, no GPU)            │
│    → extract raw text directly                      │
│                                                     │
│  Path B — Scanned PDF or image (no text layer)      │
│    → Detect: if PDF, render pages to image          │
│    → OCR: Tesseract (free) or Google Cloud Vision   │
│      or Mistral Pixtral (already in your stack)     │
│    → Output: raw text string                        │
│                                                     │
│  Path C — Structured data (rare, CSV/Excel)         │
│    → pandas read_csv / read_excel                   │
│    → convert to text summary for LLM                │
└──────────────────────────┬──────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 3: LLM CONTENT CLASSIFICATION (Relevance)   │
│                                                     │
│  LLM prompt: "Is this a financial bill, receipt,   │
│  or bank statement? What type? Is it genuine?"      │
│                                                     │
│  Output: { type, is_valid, confidence }             │
│  Reject if: is_valid=false or confidence < 0.6      │
│                                                     │
│  Accepted types:                                    │
│  rent_receipt, electricity, water, gas, phone,      │
│  school_fees, emi_receipt, insurance_premium,       │
│  bank_statement, municipal_tax                      │
│                                                     │
│  Rejected: random documents, screenshots,           │
│  non-financial content, unreadable files            │
└──────────────────────────┬──────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 4: STRUCTURED EXTRACTION (LLM)               │
│                                                     │
│  Extract per bill:                                  │
│  {                                                  │
│    bill_type: "rent_receipt",                       │
│    amount: 8500,                                    │
│    currency: "INR",                                 │
│    payment_date: "2024-01-05",                      │
│    billing_period: "January 2024",                  │
│    payee_name: "Rajan Properties",                  │
│    payer_name: "Karan Mehta",                       │
│    verification_level: "document_uploaded",         │
│    is_recurring: true                               │
│  }                                                  │
└──────────────────────────┬──────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 5: CONSISTENCY ANALYSIS                      │
│                                                     │
│  Group by bill_type + payee                         │
│  Build timeline: which months are covered?          │
│  Calculate:                                         │
│  • consistency_score = covered_months / window      │
│  • streak = longest unbroken consecutive months     │
│  • variance = std deviation of amounts              │
│    (consistent amount = genuine, wild variance = ?) │
└──────────────────────────┬──────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  STAGE 6: SCORING + REASON GENERATION               │
│                                                     │
│  Score per bill stream + overall bill agent score   │
│  Generate human-readable reasons per document       │
│  Pass to CreditBridge coordinator agent             │
└─────────────────────────────────────────────────────┘
```

---

## 3. Scoring Formula (My Recommendation)

### Per Bill Stream Score (0–100)

```
stream_score = (
    bill_type_weight   ×  0.35   +   # what type of bill
    consistency_score  ×  0.40   +   # how consistent (months covered)
    amount_signal      ×  0.15   +   # financial commitment level
    verification_bonus ×  0.10       # how verified is it
)
```

### Bill Type Weights (bill_type_weight)

| Bill Type | Weight | Why |
|---|---|---|
| Rent | 1.5 | Lose home if you stop — highest stakes |
| EMI / Loan repayment | 1.4 | Asset repossession risk |
| School Fees | 1.3 | Long-term family commitment |
| Electricity | 1.0 | Essential, standardized format, easy to verify |
| Water / Gas | 0.9 | Essential but lower amounts |
| Insurance Premium | 1.1 | Deliberate financial planning behavior |
| Municipal Tax | 1.2 | Shows property ownership or tenancy |
| Phone Bill | 0.7 | Lowest stakes — original signal, now baseline |

### Consistency Score

```python
# Months covered in last 12
consistency_score = min(covered_months / 12, 1.0)

# Bonus for streak
streak_bonus = (longest_streak / 12) * 0.1

# Penalty for gaps
gap_penalty = num_gaps * 0.05
```

### Amount Signal (amount_signal)

This normalizes the bill amount to a 0–1 signal against regional income proxies:

```
Low:       < ₹500/mo    → 0.3
Medium:    ₹500–₹3000   → 0.6
High:      ₹3000–₹10000 → 0.9
Very High: > ₹10000     → 1.0
```

Higher is not always better — a ₹50,000 "rent bill" from an unverified source is suspicious. LLM flags outliers.

### Verification Levels (verification_bonus)

| Source | Bonus |
|---|---|
| Bank statement debit match | +10 pts (highest trust) |
| Account Aggregator linked | +10 pts |
| PDF bill uploaded | +5 pts |
| Image uploaded | +3 pts |
| Self-reported | +0 pts (flagged in bank officer view) |

### Final Bill Agent Score

```
final_bill_score = weighted_average(all stream_scores)
                 × diversity_multiplier   # 1.0 for 1 type, 1.2 for 3+ types
                 × volume_factor          # more months of data = higher confidence
```

---

## 4. Validation Catches (Critical)

These guardrails prevent abuse and keep the system trustworthy:

### File-Level Guardrails

| Check | Rule |
|---|---|
| File type whitelist | Only PDF, JPG, JPEG, PNG |
| File size | Max 5MB per file |
| Max uploads | 10 files per application |
| Minimum resolution | Images > 300px wide (OCR quality check) |
| Duplicate detection | Hash check — same file uploaded twice is rejected |

### Content-Level Guardrails (LLM-based)

| Check | Action |
|---|---|
| Not a financial document | Reject with message |
| Bill date older than 24 months | Reject as too old |
| Bill date in the future | Reject as fabricated |
| Amount = 0 or negative | Reject |
| Payer name doesn't match applicant name | Flag for bank officer review (not reject — could be joint household) |
| Amount variance > 300% across months | Flag as suspicious |
| LLM confidence < 60% | Reject — can't reliably extract |
| Same bill type, same payee, same month uploaded twice | Deduplicate, keep one |

### Anti-Gaming Guardrails

| Risk | Mitigation |
|---|---|
| Photoshopped bills | LLM checks for formatting inconsistencies; metadata checked |
| Backdated bills | Bill dates cross-referenced against upload timestamp |
| Same bill submitted for multiple applicants | Hash dedup across applicant pool |
| Fake payee name | Not fully solvable at upload time — flag for officer review |

> **IMPORTANT:** The system cannot be 100% fraud-proof at upload time. The goal is to raise the cost of fraud high enough that it becomes impractical. Bank officers see verification_level on each document — unverified self-reported documents are always flagged visually.

---

## 5. Per-Document Score Explanation

This is crucial for transparency and for the bank officer's trust in the system.

Each bill stream produces a reason card:

```json
{
  "bill_type": "rent_receipt",
  "display_name": "House Rent — Rajan Properties",
  "amount": 8500,
  "months_covered": 11,
  "consistency_score": 91,
  "stream_score": 88,
  "verification_level": "document_uploaded",
  "reason": "11 months of consistent ₹8,500 rent payments to Rajan Properties. One gap in August 2023. High-stakes obligation showing strong financial discipline. Weight: 1.5x (rent category).",
  "flag": null
}
```

The bank officer sees exactly which document contributed what, and why. No black box.

---

## 6. MongoDB Atlas Migration — POV

### Why MongoDB Atlas is Right for This Feature

**SQLite (current) limitations with this feature:**
- Bills are heterogeneous documents — rent bills have different fields than electricity bills
- Storing OCR text + extracted JSON + original file reference in flat tables is messy
- No native file storage — you'd need a separate folder or S3
- No full-text search across extracted bill content
- Scaling issues once file metadata accumulates

**MongoDB Atlas advantages:**

| Feature | Why it matters for Bill Agent |
|---|---|
| Flexible schema | Rent bill doc ≠ school fee doc. MongoDB handles this naturally |
| GridFS | Store actual PDF/image files inside MongoDB with metadata |
| Atlas Vector Search | Semantic search over OCR'd bill text (future) |
| Aggregation pipeline | Calculate consistency scores directly in DB query |
| Atlas App Services | Serverless trigger when bill is uploaded → auto-process |
| Change Streams | Real-time frontend update when processing completes |

### Proposed MongoDB Collections

```
creditbridge_db/
├── applicants/               # user profiles (replaces applicants table)
├── bill_documents/           # one doc per uploaded file + extraction results
├── bill_streams/             # aggregated per bill_type+payee consistency
├── credit_scores/            # final scores with breakdown
├── consent_logs/             # immutable audit trail
├── questionnaire_responses/
├── audit_logs/
└── agent_weights/
```

### bill_documents Collection Shape

```json
{
  "_id": "ObjectId(...)",
  "applicant_id": "uuid-of-applicant",
  "upload_timestamp": "2024-01-15T10:23:00Z",
  "original_filename": "electricity_jan.pdf",
  "file_hash": "sha256:abc123...",
  "gridfs_file_id": "ObjectId(...)",
  "stage": "scored",
  "classification": {
    "bill_type": "electricity",
    "is_valid": true,
    "confidence": 0.93,
    "llm_model": "mistral-medium-latest"
  },
  "extraction": {
    "amount": 620,
    "currency": "INR",
    "payment_date": "2024-01-08",
    "billing_period": "December 2023",
    "payee_name": "MSEDCL",
    "payer_name": "Karan Mehta"
  },
  "verification_level": "document_uploaded",
  "flags": [],
  "stream_score": 82,
  "reason": "Consistent electricity bill of ₹620 from MSEDCL..."
}
```

### Migration Strategy

**Recommended approach:** Keep SQLite for existing tables (applicants, scores, consent, audit). Add MongoDB Atlas **only for the new Bill Agent data** (bill_documents, bill_streams). This minimises migration risk while getting MongoDB's document flexibility exactly where it's needed.

Later, if the project scales, migrate the rest.

---

## 7. Open Questions

Before implementing, these design decisions need answers:

1. **OCR provider**: Tesseract (free, local, slower) OR Mistral Pixtral (existing API key, better accuracy, costs tokens)?
2. **File storage**: GridFS inside MongoDB Atlas OR S3/GCS with URL stored in MongoDB?
3. **Processing timing**: Synchronous (user waits 5-15s) or Asynchronous (upload → "processing" status → result appears)?
4. **Account Aggregator**: Real integration or UI placeholder for now?
5. **Bank officer view**: See actual uploaded bill documents, or only extracted structured data + score?

---

## Summary

| Aspect | Recommendation |
|---|---|
| Bill types | Rent, electricity, water, gas, phone, school fees, EMI, insurance, municipal tax |
| Scoring weights | Rent > EMI > school fees > insurance > electricity > water > phone |
| Consistency window | 6–12 months (12 = full score) |
| File types accepted | PDF, JPG, JPEG, PNG only |
| Extraction pipeline | pdfplumber → OCR (Pixtral) → LLM structured extract |
| Fraud guardrails | File hash dedup, date validation, LLM confidence threshold, amount variance check |
| Explanation | Per-document score card with reason text shown to bank officer |
| DB strategy | MongoDB Atlas for Bill Agent data, keep SQLite for existing tables initially |
| Processing | Async background task (better UX for 5-15s OCR processing) |
