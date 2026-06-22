"""
CreditBridge FastAPI Application
Entry point for the backend server.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes.applicant import router as applicant_router
from routes.scoring import router as scoring_router
from routes.reports import router as reports_router
from routes.admin import router as admin_router
from config import DEBUG

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CreditBridge API",
    description="AI-powered alternate credit scoring for borrowers with no credit history",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow React frontend on localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(applicant_router)
app.include_router(scoring_router)
app.include_router(reports_router)
app.include_router(admin_router)


@app.on_event("startup")
def startup():
    """Initialize database on server start."""
    logger.info("CreditBridge API starting up...")
    init_db()
    logger.info("Database initialized")


@app.get("/")
def root():
    return {
        "name": "CreditBridge API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "creditbridge-backend"}
