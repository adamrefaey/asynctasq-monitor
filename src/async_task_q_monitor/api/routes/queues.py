"""Queues routes for the monitoring UI (placeholders)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/queues")
async def list_queues() -> dict:
    """List queues (placeholder)."""
    return {"items": [], "total": 0}
