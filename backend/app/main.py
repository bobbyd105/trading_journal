"""FastAPI application entrypoint for the Phase 1 backend shell."""

from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(
    title="Trading Journal API",
    description="Local-first API for the V1-Lite trading journal.",
    version="0.1.0",
)

app.include_router(health_router)
