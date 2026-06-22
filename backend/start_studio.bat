@echo off
echo.
echo  ╔════════════════════════════════════════════════╗
echo  ║   CreditBridge — Neuro SAN Studio             ║
echo  ╚════════════════════════════════════════════════╝
echo.
echo  REQUIREMENT: Add your API key to .env first!
echo    GEMINI_API_KEY=AIzaSy...   (get free at aistudio.google.com)
echo    AGENT_MODEL_NAME=gemini/gemini-2.0-flash
echo.

cd /d %~dp0

call venv\Scripts\activate

echo Checking Neuro SAN Studio...
ns --version 2>nul || (echo ERROR: ns not found. Run: pip install neuro-san-studio && pause && exit /b 1)

echo.
echo ──────────────────────────────────────────────────────
echo  Studio UI  →  http://localhost:4173
echo.
echo  1. Open http://localhost:4173 in your browser
echo  2. Select "creditbridge" from the agent dropdown
echo  3. You should see 9 connected agents in the graph
echo  4. Type this in the chat box to test:
echo.
echo  {"applicant_id": "demo-priya-002", "consented_sources":
echo   ["phone_bill","ecommerce","geolocation","merchant","cashflow"],
echo   "questionnaire_answers": [0,0,0,0,0,0,0,0,0,0]}
echo ──────────────────────────────────────────────────────
echo.
ns run
