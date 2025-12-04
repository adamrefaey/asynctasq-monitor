"""Task-related API routes.

This module follows FastAPI 0.122+ best practices:
- Use Annotated dependencies (PEP 593)
- Use typed dependency injection with TaskServiceDep
- Use PaginationDep for consistent pagination across endpoints
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from asynctasq_monitor.api.dependencies import PaginationDep, TaskServiceDep
from asynctasq_monitor.models.task import (
    Task,
    TaskFilters,
    TaskListResponse,
    TaskStatus,
)

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={
        404: {"description": "Task not found"},
    },
)


@router.get("")
async def list_tasks(
    task_service: TaskServiceDep,
    pagination: PaginationDep,
    status: Annotated[
        TaskStatus | None,
        Query(description="Filter by task status"),
    ] = None,
    queue: Annotated[
        str | None,
        Query(description="Filter by queue name"),
    ] = None,
    search: Annotated[
        str | None,
        Query(max_length=200, description="Search in task name, ID, or args"),
    ] = None,
) -> TaskListResponse:
    """List tasks with optional filtering and pagination.

    Returns a paginated list of tasks with computed pagination info.
    """
    limit, offset = pagination
    filters = TaskFilters(status=status, queue=queue, worker_id=None, search=search)
    tasks, total = await task_service.get_tasks(filters, limit=limit, offset=offset)
    return TaskListResponse(items=tasks, total=total, limit=limit, offset=offset)


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    task_service: TaskServiceDep,
) -> Task:
    """Retrieve a single task by ID.

    Raises:
        HTTPException: 404 if task not found.
    """
    task = await task_service.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    task_service: TaskServiceDep,
) -> dict[str, str]:
    """Retry a failed task by re-enqueueing it via the driver.

    Returns:
        Success message with task ID.

    Raises:
        HTTPException: 400 if task cannot be retried.
    """
    success = await task_service.retry_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot retry task")
    return {"status": "success", "message": f"Task {task_id} re-enqueued"}


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    task_service: TaskServiceDep,
) -> dict[str, str]:
    """Delete a task by ID.

    Returns:
        Success message with task ID.

    Raises:
        HTTPException: 404 if task not found or cannot be deleted.
    """
    success = await task_service.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be deleted")
    return {"status": "success", "message": f"Task {task_id} deleted"}
