# CreditBridge — Start All 3 Services
# Run this from d:\creditbridge
# It opens each service in its own PowerShell window

$backend = "d:\creditbridge\backend"

# Terminal 1: Python FastAPI backend (port 8000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; Write-Host '=== CreditBridge Python Backend ===' -ForegroundColor Cyan; .\venv\Scripts\Activate.ps1; uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 2

# Terminal 2: Neuro SAN Studio (port 4175 / HTTP 8085)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; Write-Host '=== Neuro SAN Studio ===' -ForegroundColor Magenta; .\venv\Scripts\Activate.ps1; python -m neuro_san_studio run --server-http-port 8085 --nsflow-port 4175"

# Terminal 3: React frontend2 (port 3000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'd:\creditbridge\frontend2'; Write-Host '=== CreditBridge Frontend2 ===' -ForegroundColor Green; npm run dev"

Write-Host ""
Write-Host "All 3 services starting..." -ForegroundColor Yellow
Write-Host "  Backend API:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Neuro SAN UI: http://localhost:4175" -ForegroundColor Magenta
Write-Host "  Frontend App: http://localhost:3000" -ForegroundColor Green
