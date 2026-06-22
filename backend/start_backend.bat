@echo off
echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║   CreditBridge — FastAPI Backend Server   ║
echo  ╚═══════════════════════════════════════════╝
echo.

cd /d %~dp0

if not exist venv\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing / verifying dependencies...
pip install -r requirements.txt -q

echo.
echo Running demo seed (safe to run multiple times)...
python demo_seed.py

echo.
echo ──────────────────────────────────────────────
echo  FastAPI Server  →  http://localhost:8000
echo  Swagger Docs    →  http://localhost:8000/docs
echo ──────────────────────────────────────────────
echo.
uvicorn main:app --reload --port 8000 --host 0.0.0.0
