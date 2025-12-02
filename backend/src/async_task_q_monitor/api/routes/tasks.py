"""Task-related API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from async_task_q_monitor.api.dependencies import get_task_service
from async_task_q_monitor.models.task import (
    Task,
    TaskFilters,
    TaskListResponse,
    TaskStatus,
)
from async_task_q_monitor.services.task_service import TaskService

router = APIRouter()

# module-level dependency objects to avoid calling Depends(...) in function defaults
_get_task_service_dep = Depends(get_task_service)


@router.get("/tasks")
async def list_tasks(
    status: Annotated[TaskStatus | None, Query()] = None,
    queue: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    task_service: Annotated[TaskService, Depends(get_task_service)] = _get_task_service_dep,
) -> TaskListResponse:
    """List tasks with optional filtering and pagination."""
    filters = TaskFilters(status=status, queue=queue, worker_id=None, search=search)
    tasks, total = await task_service.get_tasks(filters, limit=limit, offset=offset)
    return TaskListResponse(items=tasks, total=total, limit=limit, offset=offset)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    task_service: Annotated[TaskService, Depends(get_task_service)] = _get_task_service_dep,
) -> Task:
    """Retrieve a single task by id, or raise HTTP 404 if not found."""
    task = await task_service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: str,
    task_service: Annotated[TaskService, Depends(get_task_service)] = _get_task_service_dep,
) -> dict:
    """Retry a failed task by re-enqueueing it via the driver."""
    success = await task_service.retry_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot retry task")
    return {"status": "success", "message": f"Task {task_id} re-enqueued"}


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    task_service: Annotated[TaskService, Depends(get_task_service)] = _get_task_service_dep,
) -> dict:
    """Delete a task by id."""
    success = await task_service.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be deleted")
    return {"status": "success", "message": f"Task {task_id} deleted"}
