"""Queue-related API routes.

This module follows FastAPI 0.122+ best practices:
- Use Annotated dependencies (PEP 593)
- Use typed dependency injection with QueueServiceDep
- Use proper HTTP status codes and response models
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from async_task_q_monitor.api.dependencies import QueueServiceDep
from async_task_q_monitor.models.queue import (
    Queue,
    QueueActionRequest,
    QueueActionResponse,
    QueueAlertLevel,
    QueueClearResponse,
    QueueFilters,
    QueueListResponse,
    QueueMetrics,
    QueueStatus,
)

router = APIRouter(
    prefix="/queues",
    tags=["queues"],
    responses={
        404: {"description": "Queue not found"},
    },
)


@router.get("")
async def list_queues(
    queue_service: QueueServiceDep,
    status: Annotated[
        QueueStatus | None,
        Query(description="Filter by queue status"),
    ] = None,
    search: Annotated[
        str | None,
        Query(max_length=200, description="Search in queue name"),
    ] = None,
    min_depth: Annotated[
        int | None,
        Query(ge=0, description="Filter queues with depth >= this value"),
    ] = None,
    alert_level: Annotated[
        QueueAlertLevel | None,
        Query(description="Filter by alert level (normal, warning, critical)"),
    ] = None,
) -> QueueListResponse:
    """List all queues with optional filtering.

    Returns a list of all queues with their current statistics.
    """
    filters = QueueFilters(
        status=status,
        search=search,
        min_depth=min_depth,
        alert_level=alert_level,
    )
    return await queue_service.get_queues(filters)


@router.get("/{queue_name}")
async def get_queue(
    queue_name: str,
    queue_service: QueueServiceDep,
) -> Queue:
    """Get detailed information about a specific queue.

    Raises:
        HTTPException: 404 if queue not found.
    """
    queue = await queue_service.get_queue_by_name(queue_name)
    if not queue:
        raise HTTPException(status_code=404, detail=f"Queue '{queue_name}' not found")
    return queue


@router.get("/{queue_name}/metrics")
async def get_queue_metrics(
    queue_name: str,
    queue_service: QueueServiceDep,
    from_time: Annotated[
        str | None,
        Query(
            description="Start time for metrics (ISO format, defaults to 24h ago)",
            alias="from",
        ),
    ] = None,
    to_time: Annotated[
        str | None,
        Query(
            description="End time for metrics (ISO format, defaults to now)",
            alias="to",
        ),
    ] = None,
    interval: Annotated[
        int,
        Query(
            ge=1,
            le=60,
            description="Aggregation interval in minutes",
        ),
    ] = 5,
) -> list[QueueMetrics]:
    """Get historical metrics for a queue.

    Returns time-series data for queue depth, throughput, and duration.

    Raises:
        HTTPException: 404 if queue not found.
    """
    # Verify queue exists
    queue = await queue_service.get_queue_by_name(queue_name)
    if not queue:
        raise HTTPException(status_code=404, detail=f"Queue '{queue_name}' not found")

    # Parse datetime strings if provided
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    parsed_from = None
    parsed_to = None

    if from_time:
        try:
            parsed_from = datetime.fromisoformat(from_time.replace("Z", "+00:00"))
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid 'from' datetime format: {e}",
            ) from e

    if to_time:
        try:
            parsed_to = datetime.fromisoformat(to_time.replace("Z", "+00:00"))
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid 'to' datetime format: {e}",
            ) from e

    # Defaults
    if parsed_from is None:
        parsed_from = now - timedelta(hours=24)
    if parsed_to is None:
        parsed_to = now

    return await queue_service.get_queue_metrics(
        queue_name,
        from_time=parsed_from,
        to_time=parsed_to,
        interval_minutes=interval,
    )


@router.post("/{queue_name}/pause")
async def pause_queue(
    queue_name: str,
    queue_service: QueueServiceDep,
    body: QueueActionRequest | None = None,
) -> QueueActionResponse:
    """Pause a queue to stop processing tasks.

    Paused queues will not dispatch tasks to workers.
    Tasks can still be enqueued to paused queues.

    Returns:
        Action response indicating success/failure.

    Raises:
        HTTPException: 404 if queue not found.
    """
    reason = body.reason if body else None
    response = await queue_service.pause_queue(queue_name, reason)

    if not response.success:
        if "not found" in response.message.lower():
            raise HTTPException(status_code=404, detail=response.message)
        raise HTTPException(status_code=400, detail=response.message)

    return response


@router.post("/{queue_name}/resume")
async def resume_queue(
    queue_name: str,
    queue_service: QueueServiceDep,
) -> QueueActionResponse:
    """Resume a paused queue to continue processing.

    Workers will start picking up tasks from the queue again.

    Returns:
        Action response indicating success/failure.

    Raises:
        HTTPException: 404 if queue not found.
    """
    response = await queue_service.resume_queue(queue_name)

    if not response.success:
        if "not found" in response.message.lower():
            raise HTTPException(status_code=404, detail=response.message)
        raise HTTPException(status_code=400, detail=response.message)

    return response


@router.delete("/{queue_name}")
async def clear_queue(
    queue_name: str,
    queue_service: QueueServiceDep,
) -> QueueClearResponse:
    """Clear all pending tasks from a queue.

    WARNING: This is a destructive operation that cannot be undone.
    All pending tasks will be permanently deleted.

    Currently running tasks are not affected.

    Returns:
        Clear response with count of deleted tasks.

    Raises:
        HTTPException: 404 if queue not found.
    """
    response = await queue_service.clear_queue(queue_name)

    if not response.success:
        if "not found" in response.message.lower():
            raise HTTPException(status_code=404, detail=response.message)
        raise HTTPException(status_code=400, detail=response.message)

    return response
