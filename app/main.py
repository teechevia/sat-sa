"""
SAT-SA FastAPI Application Entry Point
========================================
Stage 5 implementation.

Run development server:
    uvicorn app.main:app --reload

Swagger documentation:
    http://localhost:8000/docs
    http://localhost:8000/openapi.json
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.data_access import load_api_data
from app.routers import findings, metrics, organizations


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup lifespan hook — initializes API caches from Stage 3 & 4 JSON files."""
    load_api_data()
    yield


app = FastAPI(
    title="SAT-SA Supervisory Assessment Tool",
    description=(
        "Independent Supervisory Assessment System for Security Operations.\n\n"
        "Analyzes periodic SOC operational evidence, surfaces prioritized findings "
        "with record traceability, and assists human supervisory assessment."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS Configuration (Local development origins)
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health Endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check endpoint",
    description="Fast health check verifying system availability without running expensive pipeline tasks.",
)
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "SAT-SA",
        "version": "0.1.0",
    }


# ---------------------------------------------------------------------------
# Include API Routers
# ---------------------------------------------------------------------------
app.include_router(organizations.router)
app.include_router(findings.router)
app.include_router(metrics.router)
