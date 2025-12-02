"""Pydantic models used by the async_task_q_monitor API."""

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from async_task_q.core.models import TaskInfo


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Complete task representation for monitoring."""

    # Identity
    id: str = Field(..., description="Unique task ID (UUID)")
    name: str = Field(..., description="Task function name (e.g., 'send_email')")
    queue: str = Field(..., description="Queue name task belongs to")

    # Status & Timing
    status: TaskStatus
    enqueued_at: datetime = Field(..., description="When task was added to queue")
    started_at: datetime | None = Field(None, description="When worker started processing")
    completed_at: datetime | None = Field(
        None,
        description="When task finished (success or failure)",
    )
    duration_ms: int | None = Field(None, description="Execution time in milliseconds")

    # Execution Context
    worker_id: str | None = Field(None, description="Worker ID processing this task")
    attempt: int = Field(1, description="Current retry attempt number")
    max_retries: int = Field(3, description="Maximum retry attempts allowed")

    # Task Data
    args: list[Any] = Field(default_factory=list, description="Positional arguments")
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Keyword arguments")

    # Result/Error
    result: Any | None = Field(None, description="Task return value (if successful)")
    exception: str | None = Field(None, description="Exception message (if failed)")
    traceback: str | None = Field(None, description="Full exception traceback")

    # Metadata
    priority: int = Field(0, description="Task priority (higher = more important)")
    timeout_seconds: int | None = Field(None, description="Execution timeout")
    tags: list[str] = Field(default_factory=list, description="Custom tags for filtering")

    class Config:
        """Pydantic configuration for examples."""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "send_email",
                "queue": "emails",
                "status": "completed",
                "enqueued_at": "2025-11-28T10:00:00Z",
                "started_at": "2025-11-28T10:00:05Z",
                "completed_at": "2025-11-28T10:00:07Z",
                "duration_ms": 2150,
                "worker_id": "worker-1",
                "attempt": 1,
                "max_retries": 3,
                "args": ["user@example.com"],
                "kwargs": {"subject": "Welcome!"},
                "result": {"sent": True, "message_id": "abc123"},
                "priority": 0,
                "timeout_seconds": 60,
                "tags": ["transactional"],
            },
        }

    @classmethod
    def from_task_info(cls, task_info: TaskInfo) -> "Task":
        """Convert core TaskInfo dataclass to rich Pydantic Task model."""
        return cls(
            id=task_info.id,
            name=task_info.name,
            queue=task_info.queue,
            status=TaskStatus(task_info.status),
            enqueued_at=task_info.enqueued_at,
            started_at=task_info.started_at,
            completed_at=task_info.completed_at,
            duration_ms=task_info.duration_ms,
            worker_id=task_info.worker_id,
            attempt=task_info.attempt,
            max_retries=task_info.max_retries,
            args=task_info.args or [],
            kwargs=task_info.kwargs or {},
            result=task_info.result,
            exception=task_info.exception,
            traceback=task_info.traceback,
            priority=task_info.priority,
            timeout_seconds=task_info.timeout_seconds,
            tags=task_info.tags or [],
        )


class TaskFilters(BaseModel):
    """Filters for task list queries."""

    status: TaskStatus | None = None
    queue: str | None = None
    worker_id: str | None = None
    search: str | None = Field(None, description="Search in task name, ID, or args")
    from_date: datetime | None = None
    to_date: datetime | None = None
    tags: list[str] | None = None


class TaskListResponse(BaseModel):
    """Simple paginated response for task list endpoints."""

    items: list[Task]
    total: int
    limit: int = 50
    offset: int = 0
