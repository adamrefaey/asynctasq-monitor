"""Workers API endpoints for the monitor application.

This module provides RESTful endpoints for worker monitoring and management:
- List and filter workers
- Get worker details and task history
- Management actions (pause, resume, shutdown, kill)
- Worker logs streaming
- Heartbeat processing

Following FastAPI 0.122+ best practices:
- Annotated dependencies (PEP 593)
- Response models for OpenAPI docs
- Async throughout for non-blocking I/O
- Proper HTTP status codes and error handling
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from asynctasq_monitor.api.dependencies import WorkerServiceDep
from asynctasq_monitor.models.worker import (
    HeartbeatRequest,
    HeartbeatResponse,
    Worker,
    WorkerAction,
    WorkerActionRequest,
    WorkerActionResponse,
    WorkerDetail,
    WorkerFilters,
    WorkerListResponse,
    WorkerLogsResponse,
    WorkerStatus,
)

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get(
    "",
    response_model=WorkerListResponse,
    summary="List all workers",
    description="Get a paginated list of workers with optional filtering by status, queue, or search term.",
)
async def list_workers(
    service: WorkerServiceDep,
    status: Annotated[
        WorkerStatus | None,
        Query(description="Filter by worker status"),
    ] = None,
    queue: Annotated[
        str | None,
        Query(description="Filter by queue name"),
    ] = None,
    search: Annotated[
        str | None,
        Query(description="Search workers by name, ID, or hostname"),
    ] = None,
    is_paused: Annotated[
        bool | None,
        Query(description="Filter by paused state"),
    ] = None,
    has_current_task: Annotated[
        bool | None,
        Query(description="Filter by whether worker is processing a task"),
    ] = None,
) -> WorkerListResponse:
    """Return a typed, filtered list of workers.

    Supports filtering by:
    - status: active, idle, or offline
    - queue: workers processing a specific queue
    - search: text search on name, ID, hostname
    - is_paused: workers in paused state
    - has_current_task: workers currently processing
    """
    filters = WorkerFilters(
        status=status,
        queue=queue,
        search=search,
        is_paused=is_paused,
        has_current_task=has_current_task,
    )
    return await service.get_workers(filters)


@router.get(
    "/{worker_id}",
    response_model=Worker,
    summary="Get worker by ID",
    description="Get basic information about a specific worker.",
    responses={404: {"description": "Worker not found"}},
)
async def get_worker(
    service: WorkerServiceDep,
    worker_id: str,
) -> Worker:
    """Get a single worker by ID."""
    worker = await service.get_worker_by_id(worker_id)
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )
    return worker


@router.get(
    "/{worker_id}/detail",
    response_model=WorkerDetail,
    summary="Get worker details",
    description="Get detailed information about a worker including task history and performance metrics.",
    responses={404: {"description": "Worker not found"}},
)
async def get_worker_detail(
    service: WorkerServiceDep,
    worker_id: str,
) -> WorkerDetail:
    """Get detailed worker information including task history."""
    detail = await service.get_worker_detail(worker_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )
    return detail


@router.post(
    "/{worker_id}/action",
    response_model=WorkerActionResponse,
    summary="Perform worker action",
    description="Execute a management action on a worker: pause, resume, shutdown, or kill.",
    responses={
        404: {"description": "Worker not found"},
        400: {"description": "Action not allowed for current worker state"},
    },
)
async def perform_worker_action(
    service: WorkerServiceDep,
    worker_id: str,
    request: WorkerActionRequest,
) -> WorkerActionResponse:
    """Perform a management action on a worker.

    Available actions:
    - pause: Stop accepting new tasks (finishes current task)
    - resume: Resume accepting tasks after pause
    - shutdown: Graceful shutdown after current task completes
    - kill: Immediate termination (may lose current task)
    """
    response = await service.perform_action(
        worker_id,
        request.action,
        force=request.force,
    )
    if not response.success and "not found" in response.message.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.message,
        )
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message,
        )
    return response


@router.post(
    "/{worker_id}/pause",
    response_model=WorkerActionResponse,
    summary="Pause worker",
    description="Pause a worker - it will finish its current task but not accept new ones.",
    responses={
        404: {"description": "Worker not found"},
        400: {"description": "Worker already paused or offline"},
    },
)
async def pause_worker(
    service: WorkerServiceDep,
    worker_id: str,
) -> WorkerActionResponse:
    """Pause a worker from accepting new tasks."""
    return await _perform_action(service, worker_id, WorkerAction.PAUSE)


@router.post(
    "/{worker_id}/resume",
    response_model=WorkerActionResponse,
    summary="Resume worker",
    description="Resume a paused worker to accept new tasks.",
    responses={
        404: {"description": "Worker not found"},
        400: {"description": "Worker is not paused"},
    },
)
async def resume_worker(
    service: WorkerServiceDep,
    worker_id: str,
) -> WorkerActionResponse:
    """Resume a paused worker."""
    return await _perform_action(service, worker_id, WorkerAction.RESUME)


@router.post(
    "/{worker_id}/shutdown",
    response_model=WorkerActionResponse,
    summary="Graceful shutdown",
    description="Request graceful shutdown - worker will stop after completing current task.",
    responses={
        404: {"description": "Worker not found"},
        400: {"description": "Worker already offline"},
    },
)
async def shutdown_worker(
    service: WorkerServiceDep,
    worker_id: str,
) -> WorkerActionResponse:
    """Request graceful shutdown of a worker."""
    return await _perform_action(service, worker_id, WorkerAction.SHUTDOWN)


@router.post(
    "/{worker_id}/kill",
    response_model=WorkerActionResponse,
    summary="Kill worker immediately",
    description="Immediately terminate worker process. Warning: current task may be lost.",
    responses={
        404: {"description": "Worker not found"},
        400: {"description": "Worker already offline"},
    },
)
async def kill_worker(
    service: WorkerServiceDep,
    worker_id: str,
    force: Annotated[
        bool,
        Query(description="Force kill without confirmation warning"),
    ] = False,
) -> WorkerActionResponse:
    """Kill a worker immediately."""
    return await _perform_action(service, worker_id, WorkerAction.KILL, force=force)


@router.get(
    "/{worker_id}/logs",
    response_model=WorkerLogsResponse,
    summary="Get worker logs",
    description="Retrieve logs from a worker with optional filtering by level or search term.",
    responses={404: {"description": "Worker not found"}},
)
async def get_worker_logs(
    service: WorkerServiceDep,
    worker_id: str,
    level: Annotated[
        str | None,
        Query(description="Filter by log level (INFO, WARNING, ERROR, DEBUG)"),
    ] = None,
    search: Annotated[
        str | None,
        Query(description="Search within log messages"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=1000, description="Maximum logs to return"),
    ] = 100,
    offset: Annotated[
        int,
        Query(ge=0, description="Pagination offset"),
    ] = 0,
) -> WorkerLogsResponse:
    """Get logs from a specific worker."""
    response = await service.get_worker_logs(
        worker_id,
        level=level,
        search=search,
        limit=limit,
        offset=offset,
    )
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )
    return response


@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
    summary="Worker heartbeat",
    description="Process a heartbeat from a worker. Returns any pending actions.",
    status_code=status.HTTP_200_OK,
)
async def process_heartbeat(
    service: WorkerServiceDep,
    request: HeartbeatRequest,
) -> HeartbeatResponse:
    """Process heartbeat from a worker.

    Workers should call this endpoint periodically (e.g., every 30 seconds)
    to report their status. The response includes any pending commands
    like pause or shutdown requests.
    """
    return await service.handle_heartbeat(request)


async def _perform_action(
    service: WorkerServiceDep,
    worker_id: str,
    action: WorkerAction,
    *,
    force: bool = False,
) -> WorkerActionResponse:
    """Helper to perform an action and raise appropriate HTTP exceptions."""
    response = await service.perform_action(worker_id, action, force=force)
    if not response.success:
        if "not found" in response.message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=response.message,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message,
        )
    return response
