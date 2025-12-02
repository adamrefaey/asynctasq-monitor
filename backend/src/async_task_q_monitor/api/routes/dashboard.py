"""Dashboard routes for the monitoring UI (simple placeholders)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["dashboard"])
async def dashboard_root() -> dict:
    """Root dashboard health endpoint."""
    return {"status": "ok", "service": "dashboard"}


@router.get("/dashboard/summary")
async def summary() -> dict:
    """Return a small dashboard summary."""
    return {"total": 0, "pending": 0, "running": 0, "failed": 0}
