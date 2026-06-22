# CreditBridge

Alternate credit scoring system designed for the PSB Hackathon 2026. Built with FastAPI, SQLite, and Neuro SAN.

## Project Structure

```
creditbridge/
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── demo_seed.py
│   ├── routes/
│   │   ├── applicant.py
│   │   ├── scoring.py
│   │   ├── reports.py
│   │   └── admin.py
│   ├── agents/
│   │   ├── runner.py
│   │   ├── registries/
│   │   │   ├── manifest.hocon
│   │   │   └── creditbridge.hocon
│   │   └── coded_tools/
│   │       └── creditbridge/
│   │           ├── phone_bill_tool.py
│   │           ├── ecommerce_tool.py
│   │           ├── geolocation_tool.py
│   │           ├── merchant_tool.py
│   │           └── cashflow_tool.py
│   └── data/
│       └── synthetic_generator.py
├── frontend/
│   ├── src/
│   │   └── api/
│   │       └── client.js
```

## How to Run

### Backend Setup

1. **Navigate to the backend directory and set up a virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate          # Windows
   # source venv/bin/activate     # Mac/Linux
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Copy `.env.example` to `.env` and configure your keys:
   ```bash
   cp .env.example .env
   ```

4. **Seed the demo database:**
   ```bash
   python demo_seed.py
   ```

5. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

Verify by navigating to `http://localhost:8000/docs` in your browser.

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install node dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```
