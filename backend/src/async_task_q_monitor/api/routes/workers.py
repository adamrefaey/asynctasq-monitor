"""Workers endpoints (placeholder)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/workers")
async def list_workers() -> dict:
    """List workers (placeholder)."""
    return {"items": [], "total": 0}
