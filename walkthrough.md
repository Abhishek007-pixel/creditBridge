# Project Progress Report & Technical Walkthrough
## CreditBridge — ALTERNATE CREDIT SCORING SYSTEM
*PSB Hackathon 2026 | UCO Bank × Department of Financial Services × Ministry of Finance*

---

## Session Log

| Session | Date & Time (IST) | Work Done |
|---|---|---|
| Session 1 | 2026-06-22, 11:00 AM – 1:00 PM | Full backend build, agent HOCON, coded tools, FastAPI routes, frontend scaffold |
| Session 2 | 2026-06-22, 5:30 PM – 6:30 PM | Full Neuro SAN Studio setup, fixed all class paths, runner rewrite, test suite |
| Session 3 | 2026-06-22, 6:45 PM – 7:00 PM | Fixed manifest mapping format to resolve "not found" issue in Neuro SAN Studio |


---

## 1. Session 1 — Initial Build (2026-06-22, ~11:00 AM IST)

We built a fully functional prototype for **CreditBridge**. The setup integrates a FastAPI backend with a Neuro SAN multi-agent scoring network.

### **A. Core Backend Architecture**
* **Dependencies:** [requirements.txt](file:///d:/creditbridge/backend/requirements.txt) with updated flexible dependency constraints.
* **Environment Configuration:** [.env.example](file:///d:/creditbridge/backend/.env.example) and local [.env](file:///d:/creditbridge/backend/.env) (pre-seeded with a cryptographically secure JWT secret key).
* **Configuration Loader:** [config.py](file:///d:/creditbridge/backend/config.py) loading database connection parameters, default scoring weights, risk bands, and demo credentials.
* **Database Access Object:** [database.py](file:///d:/creditbridge/backend/database.py) setting up SQLite schemas (`applicants`, `credit_scores`, `consent_logs`, `audit_log`, `agent_weights`, `questionnaire_responses`) and immutable audit trails.
* **Security & Auth:** [auth.py](file:///d:/creditbridge/backend/auth.py) managing Fernet AES-256 field encryption for PII protection, bcrypt password hashing, and SHA-256 one-way hashing for Aadhaar.

### **B. Advanced Scoring & Tools Logic**
* **Alternative Data Engine:** [synthetic_generator.py](file:///d:/creditbridge/backend/data/synthetic_generator.py) generating deterministic scoring vectors from phone bill payments, bank cashflows, geolocation, e-commerce, merchant ratings, and psychometric profiles.
* **9-Agent HOCON Configuration:** [manifest.hocon](file:///d:/creditbridge/backend/agents/registries/manifest.hocon) and [creditbridge.hocon](file:///d:/creditbridge/backend/agents/registries/creditbridge.hocon).
* **Agent Coded Tools:** Wrappers fetching alternative data for scoring:
  * [phone_bill_tool.py](file:///d:/creditbridge/backend/agents/coded_tools/creditbridge/phone_bill_tool.py)
  * [ecommerce_tool.py](file:///d:/creditbridge/backend/agents/coded_tools/creditbridge/ecommerce_tool.py)
  * [geolocation_tool.py](file:///d:/creditbridge/backend/agents/coded_tools/creditbridge/geolocation_tool.py)
  * [merchant_tool.py](file:///d:/creditbridge/backend/agents/coded_tools/creditbridge/merchant_tool.py)
  * [cashflow_tool.py](file:///d:/creditbridge/backend/agents/coded_tools/creditbridge/cashflow_tool.py)
* **Agent Runner:** [runner.py](file:///d:/creditbridge/backend/agents/runner.py) orchestrating direct connections or local deterministic synthetic fallbacks.

### **C. FastAPI Routing Handlers**
* [applicant.py](file:///d:/creditbridge/backend/routes/applicant.py) (registration, auth, and consent logs).
* [scoring.py](file:///d:/creditbridge/backend/routes/scoring.py) (triggers scoring orchestration and updates database).
* [reports.py](file:///d:/creditbridge/backend/routes/reports.py) (credit report retrievals and audit trails).
* [admin.py](file:///d:/creditbridge/backend/routes/admin.py) (scoring weights tuner and dashboard statistics).
* [main.py](file:///d:/creditbridge/backend/main.py) (FastAPI app config, CORS policies, and server startup database triggers).

### **D. Seeding & Testing Scripts**
* [demo_seed.py](file:///d:/creditbridge/backend/demo_seed.py) (pre-populating the database with 5 distinct demo applicants).

### **E. Frontend API Integration Client**
* Vite + React starter initialized inside `/frontend`.
* [client.js](file:///d:/creditbridge/frontend/src/api/client.js) (Axios client with automatic JWT authorization header injection).

---

## 2. Session 2 — Neuro SAN Studio Full Setup (2026-06-22, ~5:30 PM IST)

This session fixed all the critical issues that prevented Neuro SAN Studio (`ns run`) from loading the CreditBridge agent graph, and completely rewrote the runner to use the correct v0.6.x API.

### **What Was Changed & Why**

#### **2.1 — `.env` & `.env.example` restructured** *(~5:35 PM)*
- **File:** [.env](file:///d:/creditbridge/backend/.env), [.env.example](file:///d:/creditbridge/backend/.env.example)
- **Change:** Reorganized with clear section headers (LLM Provider, Model, Backend Config, Neuro SAN Config, Feature Flags). Updated `AGENT_MANIFEST_FILE` from `agents/registries/manifest.hocon` → `registries/manifest.hocon`.
- **Why:** The old path was pointing to the internal FastAPI-only folder. Neuro SAN Studio (`ns run`) expects the manifest at `registries/manifest.hocon` relative to the working directory (backend root).

#### **2.2 — `config.py` rewritten with smart key detection** *(~5:36 PM)*
- **File:** [config.py](file:///d:/creditbridge/backend/config.py)
- **Change:** Added `get_active_api_key()` function. It auto-detects which of the three providers (Gemini, Mistral, OpenAI) has a valid key set (ignoring placeholder strings). Also maps `GEMINI_API_KEY` → `GOOGLE_API_KEY` (which is what Neuro SAN actually reads internally).
- **Why:** Previously config.py exposed raw key variables but there was no logic to detect which one was active. The runner had to check all three manually — now it calls one function.

#### **2.3 — Studio-compatible folder structure created** *(~5:40 PM)*
- **New folders:** `backend/registries/`, `backend/coded_tools/creditbridge/`
- **New files:** `backend/coded_tools/__init__.py`, `backend/coded_tools/creditbridge/__init__.py`
- **Why:** Neuro SAN Studio resolves coded tool class paths like `coded_tools.creditbridge.phone_bill_tool.PhoneBillScoringTool` starting from the directory where `ns run` is executed (i.e., `backend/`). The old path `agents.coded_tools.creditbridge.*` worked for the internal runner but not for the studio process.

#### **2.4 — `backend/registries/manifest.hocon` created** *(~5:41 PM)*
- **File:** [registries/manifest.hocon](file:///d:/creditbridge/backend/registries/manifest.hocon)
- **Content:** `{"creditbridge": "registries/creditbridge.hocon"}`
- **Why:** This is the entry point that `ns run` reads when it starts. Without this file at the root `registries/` folder, the studio would not find the CreditBridge agent graph and only show default demo agents.

#### **2.5 — `backend/registries/creditbridge.hocon` created** *(~5:42 PM)*
- **File:** [registries/creditbridge.hocon](file:///d:/creditbridge/backend/registries/creditbridge.hocon)
- **Change:** Complete 9-agent HOCON definition rewritten with corrected coded tool class paths — all using `coded_tools.creditbridge.*` prefix (no `agents.` prefix). Updated default model to `gemini/gemini-2.0-flash`.
- **Why:** The old HOCON in `agents/registries/` used `agents.coded_tools.creditbridge.*` paths which work only when FastAPI starts the runner in-process. The studio spawns a separate Python process with `backend/` as the working directory, so paths must be relative to that root.

#### **2.6 — All 5 coded tools rewritten in both locations** *(~5:45 PM)*
- **Files (both locations):** `coded_tools/creditbridge/` and `agents/coded_tools/creditbridge/`
  - [phone_bill_tool.py](file:///d:/creditbridge/backend/coded_tools/creditbridge/phone_bill_tool.py)
  - [ecommerce_tool.py](file:///d:/creditbridge/backend/coded_tools/creditbridge/ecommerce_tool.py)
  - [geolocation_tool.py](file:///d:/creditbridge/backend/coded_tools/creditbridge/geolocation_tool.py)
  - [merchant_tool.py](file:///d:/creditbridge/backend/coded_tools/creditbridge/merchant_tool.py)
  - [cashflow_tool.py](file:///d:/creditbridge/backend/coded_tools/creditbridge/cashflow_tool.py)
- **Change:** Replaced the old single `sys.path.insert` with a loop that tries **both** 3 and 4 levels up from `__file__`. This means the same file works correctly regardless of whether it's loaded by the studio (`coded_tools/creditbridge/`) or by the FastAPI runner (`agents/coded_tools/creditbridge/`).
- **Why:** The depth from `__file__` to the backend root differs between the two locations (3 levels vs 4 levels), so a single hardcoded path insert would break one of the two modes.

#### **2.7 — `agents/runner.py` completely rewritten** *(~5:50 PM)*
- **File:** [agents/runner.py](file:///d:/creditbridge/backend/agents/runner.py)
- **Change:** Replaced the old `from neuro_san.client.agent_session import AgentSession` (which does not exist in neuro-san v0.6.x) with `from neuro_san.client.direct_agent_session_factory import DirectAgentSessionFactory`. Also integrated `get_active_api_key()` from the new config. Added `GOOGLE_API_KEY` alias injection for Gemini.
- **Why:** `neuro_san.client.agent_session` was the old import path. In v0.6.60 (the installed version), the correct module is `neuro_san.client.direct_agent_session_factory`. This was causing the real agent pipeline to silently fail and always fall back to synthetic even when a valid API key was set.

#### **2.8 — `test_agents.py` fully rewritten** *(~5:55 PM)*
- **File:** [test_agents.py](file:///d:/creditbridge/backend/test_agents.py)
- **Change:** Added two-phase test suite: (1) imports and invokes all 5 coded tools directly, (2) runs full synthetic pipeline against 3 demo applicants with expected score ranges. Supports `--agents` flag for real Neuro SAN mode and `--verbose` for signal breakdown output.
- **Why:** The old test_agents.py only printed raw JSON with no pass/fail logic. The new version is a proper verification script that confirms the system is working before a demo.

#### **2.9 — Start scripts created** *(~6:00 PM)*
- **Files:** [start_backend.bat](file:///d:/creditbridge/backend/start_backend.bat), [start_studio.bat](file:///d:/creditbridge/backend/start_studio.bat)
- **Why:** One-click launchers so the user (or a judge at the hackathon) doesn't need to remember the activation commands.

### **Test Results (2026-06-22, 6:06 PM IST) — ALL PASSED ✅**

```
Test 1 — Coded Tool Imports & Invocations
  ✓ PhoneBillScoringTool     score=56  status=success
  ✓ EcommerceScoringTool     score=60  status=success
  ✓ GeolocationScoringTool   score=45  status=success
  ✓ MerchantScoringTool      score=65  status=success
  ✓ CashflowScoringTool      score=40  status=success

Test 2 — Scoring Pipeline (SYNTHETIC)
  ✓ Priya Sharma   → 635/850  Medium Risk     Rs 1,00,000 @ 15.0%
  ✓ Ravi Kumar     → 685/850  Low-Medium Risk Rs 3,00,000 @ 12.0%
  ✓ Mohammed Ishaq → 495/850  Medium-High     Rs    50,000 @ 18.0%

Overall: ALL TESTS PASSED
```

---

## 3. Changes in Our Thought Process and Rationale

### **1. Loosening Package Pin Constraints (`requirements.txt`)**
* **Initial Plan:** Hardcode exact pinned versions for packages like `pydantic==2.7.1` and `httpx==0.27.0`.
* **Change:** Loosened pins to ranges (`pydantic>=2.9.2` and `httpx>=0.28.1`).
* **Why:** The `neuro-san` library depends on newer versions of `pydantic` and `httpx`. Keeping strict pins caused installation crashes. Loosening the pins allowed `pip` to automatically resolve optimal versions while keeping dependencies conflict-free.

### **2. Dynamic Multi-Provider API Key Support & Model Override**
* **Initial Plan:** Hardcode the backend to only expect `MISTRAL_API_KEY` and fallback to synthetic scoring if absent.
* **Change:** System now auto-detects whichever of `GEMINI_API_KEY`, `MISTRAL_API_KEY`, or `OPENAI_API_KEY` is set and maps it to the correct environment variable name that Neuro SAN expects internally.
* **Why:** The hackathon judges (or demo audience) may have different API keys. One function call now handles all three providers without any code change.

### **3. Dual Folder Structure for Studio + Direct Mode**
* **Initial Plan:** Keep HOCON definitions in a single custom path (`agents/registries`) and load them in-process via FastAPI.
* **Change:** Maintain tools and HOCON in **two locations**: `agents/` (for FastAPI direct session) and the root `registries/` + `coded_tools/` (for `ns run` studio). Both stay in sync.
* **Why:** Neuro SAN Studio spawns its own Python process from the backend root — it cannot see the `agents/` sub-path. FastAPI loads in-process from its own working context. The dual structure is the only way to support both modes simultaneously without a symlink (which doesn't work well on Windows).

### **4. Fixed Critical Neuro SAN API Version Mismatch**
* **Initial Plan:** Use `from neuro_san.client.agent_session import AgentSession`.
* **Change:** Use `from neuro_san.client.direct_agent_session_factory import DirectAgentSessionFactory`.
* **Why:** `AgentSession` does not exist in neuro-san v0.6.60. The correct class in this version is `DirectAgentSessionFactory`. This was the root cause of all real-agent pipeline failures — the code was silently falling back to synthetic every time because of this import error.

---

## 4. How to Run

### **Synthetic Mode (no API key needed — always works)**
```powershell
cd d:\creditbridge\backend
venv\Scripts\python test_agents.py --verbose
```

### **FastAPI Backend**
```powershell
cd d:\creditbridge\backend
venv\Scripts\uvicorn main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### **React Frontend**
```powershell
cd d:\creditbridge\frontend
npm run dev
# App: http://localhost:5173
```

### **Neuro SAN Visual Studio (requires API key)**
1. Add your Gemini key to `backend/.env`:
   ```
   GEMINI_API_KEY=AIzaSy...your_real_key
   AGENT_MODEL_NAME=gemini/gemini-2.0-flash
   ```
2. Run the studio:
   ```powershell
   cd d:\creditbridge\backend
   venv\Scripts\activate
   ns run
   ```
3. Open **`http://localhost:4173`** → select **`creditbridge`** → see the 9-agent graph.
4. Test with:
   ```json
   {"applicant_id": "demo-priya-002", "consented_sources": ["phone_bill","ecommerce","geolocation","merchant","cashflow"], "questionnaire_answers": [0,0,0,0,0,0,0,0,0,0]}
   ```

---

## 5. Session 3 — Manifest Mapping Resolution (2026-06-22, ~6:45 PM IST)

During this session, we diagnosed and resolved the root cause of `creditbridge` failing to register in `ns run` (Neuro SAN Studio).

### **Root Cause Identified**
In Neuro SAN, the manifest files (`manifest.hocon`) are watched and parsed using a strict validation pipeline:
1. **Parser Skip:** The parser checks value types in the manifest configuration. Simple string mappings like `"creditbridge": "registries/creditbridge.hocon"` are rejected and skipped because they are neither a boolean nor a dictionary.
2. **Not Found Silent Error:** If mapping `"creditbridge": true` is used, the system translates the key `"creditbridge"` directly into a file lookup path (`registries/creditbridge`). Since this path lacks the `.hocon` extension, `open` fails, resulting in a silent fallback that reports `"manifest registry creditbridge not found"`.

### **Technical Resolution**
* **File:** [registries/manifest.hocon](file:///d:/creditbridge/backend/registries/manifest.hocon), [agents/registries/manifest.hocon](file:///d:/creditbridge/backend/agents/registries/manifest.hocon)
* **Changes:** Rewrote manifest entry format to point to `creditbridge.hocon` as a dictionary map:
  ```hocon
  {
      "creditbridge.hocon": {
          "serve": true
      }
  }
  ```
* **Result:** The system correctly opens and parses `creditbridge.hocon`, registering it under its core network identifier `creditbridge`. The graph is loaded cleanly by the agent runner and Neuro SAN Studio!

