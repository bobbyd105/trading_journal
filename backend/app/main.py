"""FastAPI application entrypoint for the Phase 1 backend shell."""

from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.crud import router as crud_router
from app.api.health import router as health_router

app = FastAPI(
    title="Trading Journal API",
    description="Local-first API for the V1-Lite trading journal.",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(crud_router)
app.include_router(analytics_router)
