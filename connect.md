# CreditBridge — Full Integration Guide: frontend2 → Python Backend

> **Goal**: Connect the React/Vite `frontend2` to the Python FastAPI `backend`, replacing the
> standalone Node.js `server.js` with real-time data flow through the actual AI scoring pipeline.

---

## 1. Architecture Overview

```
FRONTEND2 (React/Vite) — Port 3000
  Login.tsx             --> POST /api/auth/login  (JWT)
  ApplicantPortal.tsx   --> POST /api/register
                        --> POST /api/consent
                        --> POST /api/questionnaire
                        --> POST /api/score         <-- Triggers AI Agents
                        --> GET  /api/me
  BankDashboard.tsx     --> GET  /api/applicants
                        --> POST /api/admin/applicants/{id}/status
  AdminPanel.tsx        --> GET  /api/admin/weights
                        --> PUT  /api/admin/weights   <-- Agents reweight live
                        --> GET  /api/admin/analytics

          HTTP + JWT Bearer Token

BACKEND (FastAPI / Python) — Port 8000
  main.py             — FastAPI app + CORS
  routes/applicant.py — /api/register, /api/consent, /api/auth/*
  routes/scoring.py   — /api/score --> runs Neuro SAN agent pipeline
  routes/admin.py     — /api/admin/weights, /api/admin/analytics
  routes/reports.py   — /api/applicants/{id}/score
  agents/runner.py    — Neuro SAN + synthetic fallback
  database.py         — SQLite (creditbridge.db)

          Agent Network

NEURO SAN AGENT NETWORK
  6 specialist agents:
    phone_bill_agent   -- scores phone payment history
    cashflow_agent     -- scores bank transaction patterns
    geolocation_agent  -- scores location stability
    ecommerce_agent    -- scores purchase behavior
    merchant_agent     -- scores supplier relationships
    psychometric_agent -- scores questionnaire answers
  + 1 coordinator agent that aggregates all scores
  Driven by Mistral/Gemini LLM via AGENT_MODEL_NAME in .env
  Falls back to deterministic synthetic scoring automatically
```

---

## 2. Key Insight — Two Backends Exist (Only Use Python!)

| Layer | File | Port | Purpose |
|---|---|---|---|
| **Node.js backend (OLD)** | `frontend2/server.js` | 3001 | Standalone MongoDB server — **REPLACE THIS** |
| **Python backend (REAL)** | `backend/main.py` | 8000 | FastAPI + SQLite + Neuro SAN AI agents |

The frontend2 currently hardcodes `http://localhost:3001` everywhere pointing to Node.js.
We need to redirect everything to `http://localhost:8000` (Python) and fix 5 route differences.

---

## 3. API Route Mapping — Old → New

| Frontend2 Call | Old Node.js Route | New Python Route | Action |
|---|---|---|---|
| Login | `POST /api/auth/login` | `POST /api/auth/login` | Fix field name: `email` not `username` |
| Register | `POST /api/auth/register` | `POST /api/auth/register` | Add this route to Python |
| Session restore | `GET /api/me` | `GET /api/me` | Add `/me` route to Python |
| Save profile | `POST /api/applicants` | `POST /api/consent` | Change path + body |
| Submit score | `POST /api/scores` | `POST /api/score` | Change path + body (critical!) |
| List applicants | `GET /api/admin/applicants` | `GET /api/applicants` | Path change |
| Applicant detail | `GET /api/admin/applicants/:id` | `GET /api/applicants/{id}/score` | Path change |
| Update status | `POST /api/admin/applicants/:id/status` | `POST /api/admin/applicants/{id}/status` | Add to Python |
| Admin data | `GET /api/admin/data` | `GET /api/admin/analytics` + `GET /api/admin/weights` | Split into 2 calls |
| Save weights | `POST /api/admin/weights` | `PUT /api/admin/weights` | Method: POST → PUT |

---

## 4. Changes Needed in Python Backend

### 4.1 — Fix CORS (backend/main.py line 33)

```python
# BEFORE:
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],

# AFTER:
allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
],
```

---

### 4.2 — Add `/api/auth/register` Route (backend/routes/applicant.py)

The frontend2 sends `{ email, password, name, role }`. Add this route:

```python
class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: Optional[str] = "applicant"
    phone: Optional[str] = ""
    aadhaar_last4: Optional[str] = "0000"

@router.post("/auth/register")
def auth_register(req: AuthRegisterRequest):
    """Register a new user via email+password (frontend2 compatibility)."""
    applicant_id = new_id()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO applicants
               (id, name, phone_encrypted, email_encrypted, aadhaar_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (
                applicant_id,
                req.name or req.email.split("@")[0],
                encrypt_field(req.phone or ""),
                encrypt_field(req.email),
                hash_aadhaar(req.aadhaar_last4 or "0000"),
            )
        )
        conn.commit()

    token = create_access_token({
        "sub": req.email,
        "role": req.role,
        "uid": applicant_id,
        "name": req.name or req.email.split("@")[0],
    })
    log_audit(applicant_id, "USER_REGISTERED", {"email": req.email, "role": req.role})
    return {
        "token": token,
        "user": {
            "uid": applicant_id,
            "email": req.email,
            "role": req.role,
            "name": req.name or req.email.split("@")[0],
        }
    }
```

Also fix `LoginRequest` to accept `email` as field name:

```python
class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None   # frontend2 sends email, not username
    password: str
```

---

### 4.3 — Add `/api/me` Route (backend/routes/applicant.py)

```python
@router.get("/me")
def get_me(authorization: Optional[str] = Header(None)):
    """Session restore — returns applicant + score for the logged-in user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    uid = payload.get("uid")
    with get_db() as conn:
        applicant = conn.execute(
            "SELECT id, name FROM applicants WHERE id = ?", (uid,)
        ).fetchone()
        score = conn.execute(
            """SELECT final_score, risk_category, loan_recommended,
                      interest_rate, explanation, status
               FROM credit_scores WHERE applicant_id = ?""",
            (uid,)
        ).fetchone()

    return {
        "applicant": dict(applicant) if applicant else None,
        "score": dict(score) if score else None,
    }
```

---

### 4.4 — Add Status Update Route (backend/routes/admin.py)

```python
class StatusUpdateRequest(BaseModel):
    status: str        # "approved" or "rejected"
    decided_by: Optional[str] = None

@router.post("/applicants/{applicant_id}/status")
def update_applicant_status(
    applicant_id: str,
    req: StatusUpdateRequest,
    authorization: Optional[str] = Header(None)
):
    """Bank officer approves or rejects a scored applicant."""
    with get_db() as conn:
        conn.execute(
            "UPDATE credit_scores SET status = ? WHERE applicant_id = ?",
            (req.status, applicant_id)
        )
        conn.commit()
    log_audit(applicant_id, f"STATUS_{req.status.upper()}", {"decided_by": req.decided_by})
    return {"success": True, "status": req.status}
```

---

### 4.5 — Add `status` Column to Database (backend/database.py)

Inside `init_db()`, in the `credit_scores` CREATE TABLE block, add:

```sql
status  TEXT DEFAULT 'pending',
```

---

## 5. Changes Needed in frontend2

### 5.1 — Add Vite Proxy (frontend2/vite.config.ts)

This is the CLEANEST solution — no hardcoded port anywhere in source:

```typescript
export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': path.resolve(__dirname, '.') },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      // ADD THIS PROXY BLOCK:
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
```

---

### 5.2 — Replace All `http://localhost:3001` in Source Files

Replace every occurrence of `http://localhost:3001` with empty string (so `/api/...` remains):

| File | Lines |
|---|---|
| `frontend2/src/App.tsx` | 40 |
| `frontend2/src/components/Login.tsx` | 34, 44, 82, 107 |
| `frontend2/src/components/ApplicantPortal.tsx` | 52, 96, 141 |
| `frontend2/src/components/BankDashboard.tsx` | 42, 71, 91 |
| `frontend2/src/components/AdminPanel.tsx` | 48, 90 |

Example:
```typescript
// BEFORE:
fetch('http://localhost:3001/api/auth/login', { ... })

// AFTER:
fetch('/api/auth/login', { ... })
```

---

### 5.3 — ApplicantPortal.tsx — Score Submission Body Change (CRITICAL)

This is the most important change. The old frontend computed the score in TypeScript and sent
the result. The new Python backend expects raw answers and RUNS THE AI AGENTS ITSELF:

```typescript
// OLD (sends pre-computed score object — does NOT trigger AI agents):
await fetch('http://localhost:3001/api/scores', {
  method: 'POST',
  body: JSON.stringify({
    final_score: resultReport.final_score,
    risk_category: resultReport.risk_category,
    // ... all computed fields
  })
});

// NEW (sends only answers — Python backend runs Neuro SAN agents and computes score):
const res = await fetch('/api/score', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    applicant_id: user.uid,
    questionnaire_answers: answers,  // the 10 psychometric answer indices [0-3]
  })
});
const resultReport = await res.json();
// resultReport has the SAME fields: final_score, risk_category, breakdown, explanation, etc.
// The frontend display code DOES NOT CHANGE — only the submission body changes!
```

Also change the profile save call:

```typescript
// OLD (saves full profile to MongoDB):
await fetch('http://localhost:3001/api/applicants', {
  method: 'POST',
  body: JSON.stringify({ name, email, phone, aadhaar_last4, aadhaar_hash })
});

// NEW (saves consent flags to SQLite so Python reads them during scoring):
await fetch('/api/consent', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({
    applicant_id: user.uid,
    phone_bill: consents.phone_bill,
    ecommerce: consents.ecommerce,
    geolocation: consents.geolocation,
    merchant: consents.merchant,
    cashflow: consents.cashflow,
  })
});
```

---

### 5.4 — BankDashboard.tsx — Path Changes

```typescript
// Applicant list:
fetch('/api/applicants', ...)                         // was: /api/admin/applicants

// Applicant detail:
fetch(`/api/applicants/${app.id}/score`, ...)         // was: /api/admin/applicants/${id}

// Status update (path stays same, now works via Python Step 4.4):
fetch(`/api/admin/applicants/${id}/status`, { method: 'POST', ... })
```

---

### 5.5 — AdminPanel.tsx — Split Data Call + Method Change

```typescript
// OLD — single call to /api/admin/data:
const res = await fetch('http://localhost:3001/api/admin/data', ...);
const data = await res.json();
if (data.weights) setWeights(data.weights);
if (data.analytics) setAnalytics(data.analytics);

// NEW — two separate calls:
const [analyticsRes, weightsRes] = await Promise.all([
  fetch('/api/admin/analytics', { headers: { Authorization: `Bearer ${token}` } }),
  fetch('/api/admin/weights',   { headers: { Authorization: `Bearer ${token}` } }),
]);
const analytics  = await analyticsRes.json();
const weightsData = await weightsRes.json();
setAnalytics({
  totalApplicants: analytics.total_applicants,
  averageRating:   analytics.average_score,
  riskDistribution: Object.entries(analytics.risk_distribution || {})
    .map(([name, value]) => ({ name, value })),
  consentPenetration: [],
});
if (weightsData.weights) {
  const pct: any = {};
  for (const k in weightsData.weights) pct[k] = Math.round(weightsData.weights[k] * 100);
  setWeights(pct);
}

// Weight save — method changes POST → PUT:
await fetch('/api/admin/weights', {
  method: 'PUT',   // ← was POST
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ weights: normDecimal })
});
```

---

## 6. Real-Time Data Flow

### How Scores Appear Instantly for Bank Officers

```
[Applicant browser]                     [Python backend]                [Officer browser]
       |                                       |                               |
       |-- POST /api/score ---------------->   |                               |
       |   { applicant_id, answers }           |                               |
       |                               run_agent_pipeline()                    |
       |                                phone_bill_agent                       |
       |                                cashflow_agent                         |
       |                                geolocation_agent                      |
       |                                ecommerce_agent                        |
       |                                merchant_agent                         |
       |                                psychometric_agent                     |
       |                               save to credit_scores table             |
       |<-- ScoreReport JSON ----------        |                               |
       |                                       |          [every 5 seconds]    |
       |                                       |<-- GET /api/applicants -------|
       |                                       |-- 200 + new score ----------->|
       |                                       |                      (shows automatically!)
```

### How Admin Weight Changes Propagate

```
Admin changes sliders --> PUT /api/admin/weights --> SQLite agent_weights table
                                                           |
                                    Next scoring request:  |
                                    agents/runner.py calls get_agent_weights()
                                    --> new weights used automatically by all agents
```

---

## 7. Neuro SAN Agent Pipeline Detail

When `POST /api/score` is received:

```
routes/scoring.py
  --> read consented sources from consent_logs (SQLite)
  --> agents/runner.py: run_agent_pipeline()

  IF USE_AGENTS=true AND MISTRAL_API_KEY set:
      Neuro SAN coordinator sends tasks to 6 specialist agents
      Each agent scores one data channel (0-100)
      Coordinator applies admin-configured weights from agent_weights table
      Returns: final_score (300-850), risk_category, loan_recommended, breakdown

  IF USE_AGENTS=false OR no API key:
      Pure Python synthetic scorer (deterministic, always works, no API key needed)
      Same output shape — demo NEVER breaks

  --> INSERT result into credit_scores table
  --> Return ScoreReport JSON to frontend
```

---

## 8. Environment Variables

### backend/.env (already exists — check these values)

```env
MISTRAL_API_KEY=your_mistral_api_key_here   # set this in your actual .env file
AGENT_MODEL_NAME=mistral/mistral-medium-latest
SECRET_KEY=your_secret_key_here   # generate with: python -c "import secrets; print(secrets.token_hex(32))"
DATABASE_URL=./creditbridge.db
USE_AGENTS=true
AGENT_MANIFEST_FILE=registries/manifest.hocon
AGENT_TOOL_PATH=.
```

### frontend2/.env (create this file)

```env
# Only needed if NOT using Vite proxy (Step 5.1)
# With proxy, this file is not required
VITE_API_URL=http://localhost:8000
```

---

## 9. JWT Token Shape — Before vs After

| Field | Node.js JWT | Python JWT (after fix) |
|---|---|---|
| User ID | `uid` | `uid` (must add in Step 4.2) |
| Email | `email` | `sub` |
| Role | `role` | `role` |
| Name | not included | `name` |

After Step 4.2, Python returns exactly what frontend2 Login.tsx expects:
```json
{
  "token": "eyJ...",
  "user": { "uid": "uuid", "email": "user@email.com", "role": "applicant", "name": "Priya" }
}
```

---

## 10. Quick Demo Accounts

| Name | Email | Password | Role |
|---|---|---|---|
| Priya Sharma | priya@creditbridge.com | password123 | applicant |
| Ravi Kumar | ravi@creditbridge.com | password123 | applicant |
| UCO Bank Officer | officer@creditbridge.com | bankpass123 | officer |
| Global Admin | admin@creditbridge.com | admin123 | admin |

After Step 4.2 is implemented, clicking any quick-login button auto-registers the user on
first use (no manual DB seeding needed).

---

## 11. Start Order

### Terminal 1 — Python Backend (port 8000)

```powershell
cd d:\creditbridge\backend
.\venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 — React Frontend (port 3000)

```powershell
cd d:\creditbridge\frontend2
npm install     # first time only
npm run dev     # starts on port 3000
```

Open: **http://localhost:3000**

> Do NOT start `node server.js` — that is the old Node.js backend, now fully replaced by Python.

---

## 12. File Change Summary (Priority Order)

| # | File | What to Change | Priority |
|---|---|---|---|
| 1 | `backend/main.py` | Add `localhost:3000` to CORS | 🔴 Critical |
| 2 | `backend/routes/applicant.py` | Add `POST /api/auth/register` | 🔴 Critical |
| 3 | `backend/routes/applicant.py` | Add `GET /api/me` | 🔴 Critical |
| 4 | `frontend2/vite.config.ts` | Add Vite proxy to port 8000 | 🔴 Critical |
| 5 | `frontend2/src/components/ApplicantPortal.tsx` | Fix URLs + change score body | 🔴 Critical |
| 6 | `frontend2/src/components/Login.tsx` | Fix all URLs | 🔴 Critical |
| 7 | `frontend2/src/components/BankDashboard.tsx` | Fix URLs + paths | 🔴 Critical |
| 8 | `frontend2/src/components/AdminPanel.tsx` | Fix URLs + split data call + PUT | 🔴 Critical |
| 9 | `frontend2/src/App.tsx` | Fix URL on line 40 | 🔴 Critical |
| 10 | `backend/routes/applicant.py` | Accept `email` in LoginRequest | 🟡 Important |
| 11 | `backend/routes/admin.py` | Add `POST .../status` route | 🟡 Important |
| 12 | `backend/database.py` | Add `status` column | 🟡 Important |
| 13 | `frontend2/.env` | Create env file | 🟢 Optional |

---

## 13. Verification Tests (run after all changes)

```powershell
# Test 1: Backend is alive
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"creditbridge-backend"}

# Test 2: View all available routes
# Open in browser: http://localhost:8000/docs
```

**Browser tests:**

1. Open http://localhost:3000
2. Click "Priya Sharma (MSME)" → should reach Applicant Portal (no 3001 errors in console)
3. Complete all 3 steps → click "Generate Alternate score"
4. Check Python terminal → should show Neuro SAN pipeline running
5. Open second tab → login as UCO Bank Officer → score appears within 5 seconds
6. Login as Global Admin → change weights → save → next applicant uses new weights

---

## 14. Troubleshooting

| Error | Root Cause | Fix |
|---|---|---|
| CORS error in console | Port 3000 not in Python CORS list | Step 4.1 |
| 401 on session restore | `/api/me` route missing in Python | Step 4.3 |
| 404 on score submit | `/api/scores` vs `/api/score` path mismatch | Step 5.3 |
| Score not using agents | `USE_AGENTS=false` or missing API key | Check backend/.env |
| Weights not saving | Frontend sends POST, Python expects PUT | Step 5.5 |
| Officer sees no applicants | Wrong path `/api/admin/applicants` | Step 5.4 |
| Quick login fails | Python doesn't have `/api/auth/register` | Step 4.2 |
| Status button fails | Status route missing from Python | Step 4.4 |

---

*CreditBridge PSB Hackathon 2026 — Integration Guide*
