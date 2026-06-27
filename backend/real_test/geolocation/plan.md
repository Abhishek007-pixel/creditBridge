# Implementation Plan — Revised Geolocation Agent (GPS + Aadhaar OCR + AA Address)

This plan outlines the technical changes to revise the **`geolocation_agent`** from a purely synthetic baseline to a robust location verification agent that cross-references Live GPS coordinates, Aadhaar address documents, and Account Aggregator billing addresses.

---

## User Review Required

> [!IMPORTANT]
> **Aadhaar Privacy Compliance (UIDAI Guidelines):** 
> To comply with strict identity storage laws, the backend will **never** persist the original Aadhaar PDF/Image files, nor will it record the 12-digit Aadhaar number. Once processed by OCR and LLM, only the structured address metadata (`city`, `state`, `pin_code`) will be saved in MongoDB, and the raw uploaded file will be deleted immediately from memory/temp space.

---

## UI / User Input Requirements

To build a seamless, typing-free user experience, the frontend UI should capture inputs in two steps:

1. **Step 1: One-Click GPS Presence Verification**
   * **UI Action:** A button labeled **"Verify Live Location"**.
   * **Capture Mechanism:** When clicked, the browser triggers the standard HTML5 location prompt (`navigator.geolocation.getCurrentPosition()`).
   * **Data Captured:** Float values for `latitude` and `longitude` are automatically sent to the backend. No manual coordinates typing required.
2. **Step 2: Permanent Address Upload**
   * **UI Action:** A drag-and-drop file upload box labeled **"Upload back page of Aadhaar card"**.
   * **Capture Mechanism:** Accepts PDF or image files (`.pdf`, `.png`, `.jpg`).
   * **Data Captured:** Uploaded file is sent directly to the OCR + LLM parsing backend. No manual address typing required.

*All other addresses (e.g. Bank Statement Billing address) are auto-fetched in the background from linked Account Aggregator profiles.*

---

## Proposed Changes

We will introduce two new database collections, a new API router for coordinates/proof uploads, and refactor the coded scoring tool.

```
backend/
 ├── database_mongo.py
 ├── routes/
 │    └── geolocation.py  [NEW]
 ├── coded_tools/creditbridge/
 │    └── geolocation_tool.py
 ├── agents/coded_tools/creditbridge/
 │    └── geolocation_tool.py
 ├── run_geolocation_test.py [NEW]
 └── main.py
```

---

### 1. Database Layer

#### [MODIFY] [database_mongo.py](file:///d:/creditbridge/backend/database_mongo.py)
* Add indexes for two new collections:
  * `aadhaar_addresses` indexed on `applicant_id`.
  * `gps_verifications` indexed on `applicant_id`.
* Implement CRUD helpers:
  * `create_aadhaar_address(doc: dict) -> str`
  * `create_gps_verification(doc: dict) -> str`
  * `get_geolocation_data_for_applicant(applicant_id: str) -> dict` (Aggregates Aadhaar address, GPS log, and AA bank profile address).

---

### 2. API Router Layer

#### [NEW] [routes/geolocation.py](file:///d:/creditbridge/backend/routes/geolocation.py)
Provide endpoints to receive client-side location indicators:
* **`POST /api/geolocation/upload-aadhaar`:**
  * Accepts Aadhaar PDF/Image upload.
  * Extract text via the common `extract_document_text` helper.
  * Send text to Mistral LLM to classify as Aadhaar proof and parse address fields: `[city, state, pin_code, street]`.
  * Save to MongoDB `aadhaar_addresses` under stage `"scored"`. Delete raw file payload.
* **`POST /api/geolocation/verify-gps`:**
  * Accepts `latitude` and `longitude` from client browser.
  * Employs reverse-geocoding lookups (using a local database of Indian PIN-code coordinates or fuzzy city mapping) to resolve into a city and PIN code.
  * Save coordinate log to MongoDB `gps_verifications`.

#### [MODIFY] [main.py](file:///d:/creditbridge/backend/main.py)
* Register `routes/geolocation.py` in the FastAPI app.

---

### 3. Agent & Coded Tool Scoring Layer

#### [MODIFY] [coded_tools/creditbridge/geolocation_tool.py](file:///d:/creditbridge/backend/coded_tools/creditbridge/geolocation_tool.py)
(And sync identical copy under `agents/coded_tools/creditbridge/geolocation_tool.py`)
* Load the applicant's location profile from MongoDB.
* If any of the real inputs are missing, fallback to synthetic geolocation profiles automatically.
* If real inputs exist, score out of **100 points**:
  * **Document Alignment (40 pts):** Aadhaar PIN code vs. Bank Statement billing PIN code.
    * PIN codes match: **40 pts**
    * Cities match (but different PINs): **25 pts**
    * States match: **15 pts**
    * Discrepancy: **5 pts**
  * **Physical Proximity (40 pts):** Haversine distance between current Live GPS and registered PIN code coordinates.
    * Distance $\le 15\text{ km}$ to either Aadhaar or Bank address: **40 pts**
    * Distance $\le 50\text{ km}$: **25 pts**
    * Out-of-region: **10 pts**
  * **Address Stability (20 pts):**
    * Aadhaar or bank account active at address $\ge 12\text{ months}$: **20 pts**
    * Else: **10 pts**

---

## Verification Plan

### Automated Tests
* Create **`run_geolocation_test.py`**:
  * Ensure a test applicant exists.
  * Simulates:
    1. Uploading a mock Aadhaar card scan containing a Delhi address.
    2. Sending browser location coords corresponding to Delhi.
    3. Linking a mock AA bank profile with a matching Delhi PIN code.
  * Run the `GeolocationScoringTool` directly and print scores.
  * Save logs, results, and markdown report under `real_test/geolocation/`.
