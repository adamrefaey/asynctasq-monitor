"""Workers endpoints and simple models for the monitor app.

This module provides a lightweight, well-typed placeholder implementation
used by unit and integration tests. The models are intentionally simple so
tests can assert response shapes without requiring an actual worker
backend implementation.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class Worker(BaseModel):
    """Representation of a worker for monitoring UI tests."""

    id: str = Field(..., description="Unique worker id")
    hostname: str | None = Field(None, description="Worker host")
    status: str = Field("idle", description="Worker status: idle|busy|offline")


class WorkerListResponse(BaseModel):
    items: list[Worker]
    total: int


@router.get("/workers", response_model=WorkerListResponse)
async def list_workers() -> WorkerListResponse:
    """Return a typed, paginated list of workers.

    This is a test-friendly placeholder that returns an empty list. Tests
    should assert the response status and schema; production implementations
    can replace this router with a concrete service-backed implementation.
    """
    # Return a typed model instance to satisfy static type checkers
    return WorkerListResponse(items=[], total=0)
