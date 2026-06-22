# Project Progress Report & Technical Walkthrough
## CreditBridge — ALTERNATE CREDIT SCORING SYSTEM
*PSB Hackathon 2026 | UCO Bank × Department of Financial Services × Ministry of Finance*

---

## 1. Summary of Work Done

We have built a fully functional prototype for **CreditBridge**. The setup integrates a FastAPI backend with a Neuro SAN multi-agent scoring network.

Here are the components that have been fully created and configured:

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
* [test_agents.py](file:///d:/creditbridge/backend/test_agents.py) (direct developer validation utility to run and output agent scoring logs).

### **E. Frontend API Integration Client**
* Vite + React starter initialized inside `/frontend`.
* [client.js](file:///d:/creditbridge/frontend/src/api/client.js) (Axios client with automatic JWT authorization header injection).

---

## 2. Changes in Our Thought Process and Rationale

During development, we adjusted our approach in three main areas to make the system more robust, flexible, and aligned with standard workflows:

### **1. Loosening Package Pin Constraints (`requirements.txt`)**
* **Initial Plan:** Hardcode exact pinned versions for packages like `pydantic==2.7.1` and `httpx==0.27.0`.
* **Change:** Loosened pins to ranges (`pydantic>=2.9.2` and `httpx>=0.28.1`).
* **Why:** The `neuro-san` library depends on newer versions of `pydantic` and `httpx` (versions `2.9.2` and `0.28.1` respectively). Keeping strict pins caused installation crashes. Loosening the pins allowed `pip` to automatically resolve optimal versions while keeping dependencies conflict-free.

### **2. Dynamic Multi-Provider API Key Support & Model Override**
* **Initial Plan:** Hardcode the backend to only expect `MISTRAL_API_KEY` and fallback to synthetic scoring if absent.
* **Change:** Configured the system to accept `MISTRAL_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY` dynamically. Added `AGENT_MODEL_NAME` configuration using HOCON's default override syntax.
* **Why:** You mentioned you wanted a live LLM-backed Neuro SAN orchestration using Option 1, and since you are running Gemini in your workspace, you might want to use a Gemini key instead of Mistral. With this change, you can type **any** of the keys (OpenAI, Gemini, or Mistral) in `.env` and set `AGENT_MODEL_NAME` to your preferred model (e.g. `gemini/gemini-1.5-flash`), and the agent network will run on that provider automatically.

### **3. Compatibility with Neuro SAN Studio Server (`ns run`)**
* **Initial Plan:** Keep HOCON definitions in a custom path (`agents/registries`) and load them in-process.
* **Change:** Scaffolding the workspace in the `backend` root using `ns init`. Copying `creditbridge.hocon` to the default `registries` folder and updating `manifest.hocon` to register it. Prepended `agents.` to the coded tools class paths (e.g., `agents.coded_tools.creditbridge...`).
* **Why:** To run the official **Neuro SAN Studio UI** successfully (`ns run`), the studio expects a standard folder structure in the workspace. By adjusting the paths, the studio server is now fully capable of loading the `creditbridge` graph and resolving the custom Python coded tools without PYTHONPATH errors.

---

## 3. How to Run the Visual Agent Studio

### **1. Set your LLM API Key**
Open your [backend/.env](file:///d:/creditbridge/backend/.env) file and add your key and model. For example, if you want to use **Gemini**:
```env
GEMINI_API_KEY=AIzaSy...
AGENT_MODEL_NAME=gemini/gemini-1.5-flash
```

### **2. Start the Neuro SAN Studio Server**
From your terminal:
```powershell
cd d:\creditbridge\backend
venv\Scripts\ns run
```

* **Neuro SAN Studio Console:** Open **`http://localhost:4173/`** in your browser.
* You will see the **CreditBridge** 9-agent network visually mapped out, showing the interactions between the Coordinator, the scoring agents (Phone, Geolocation, etc.), the Synthesizer, and the Explainer. You can chat with the agents directly from the UI!
