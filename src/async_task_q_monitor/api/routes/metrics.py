"""Metrics routes for the monitoring UI (placeholders)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> dict:
    """Return some basic runtime metrics."""
    return {"uptime_seconds": 0, "tasks_processed": 0}


@router.get("/metrics/summary")
async def metrics_summary() -> dict:
    """Return a brief metrics summary structure."""
    return {"throughput": [], "duration": {}}
