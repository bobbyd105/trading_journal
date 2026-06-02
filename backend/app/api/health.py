"""Health endpoints for verifying the backend shell is running."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a minimal status payload for local development checks."""
    return {"status": "ok"}
