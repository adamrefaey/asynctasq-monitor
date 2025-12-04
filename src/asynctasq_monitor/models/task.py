"""Pydantic models used by the asynctasq_monitor API.

This module defines data models following Pydantic v2 best practices:
- Use ConfigDict for model configuration (not class-based Config)
- Use Field() with proper descriptions and constraints
- Use computed_field for derived properties
- Use model_validator for complex validation
- Prefer strict mode where appropriate
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from asynctasq.core.models import TaskInfo


class TaskStatus(str, Enum):
    """Task execution status.

    Enum values match the backend driver status strings.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Check if this status is terminal (task won't change)."""
        return self in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

    @property
    def is_active(self) -> bool:
        """Check if this status indicates the task is being processed."""
        return self in {TaskStatus.RUNNING, TaskStatus.RETRYING}


class Task(BaseModel):
    """Complete task representation for monitoring.

    This model represents a task in the queue system with all its metadata.
    It can be created from a core TaskInfo dataclass using from_task_info().

    Example:
        >>> task = Task(
        ...     id="abc-123",
        ...     name="send_email",
        ...     queue="emails",
        ...     status=TaskStatus.PENDING,
        ...     enqueued_at=datetime.now(UTC),
        ... )
    """

    model_config = ConfigDict(
        # Validate data on assignment (not just construction)
        validate_assignment=True,
        # Use enum values in JSON output
        use_enum_values=True,
        # Strict mode for better type safety
        strict=False,  # Allow coercion for API responses
        # JSON schema example for OpenAPI docs
        json_schema_extra={
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
        },
    )

    # Identity
    id: Annotated[str, Field(description="Unique task ID (UUID)")]
    name: Annotated[str, Field(description="Task function name (e.g., 'send_email')")]
    queue: Annotated[str, Field(description="Queue name task belongs to")]

    # Status & Timing
    status: TaskStatus
    enqueued_at: Annotated[datetime, Field(description="When task was added to queue")]
    started_at: Annotated[
        datetime | None,
        Field(default=None, description="When worker started processing"),
    ]
    completed_at: Annotated[
        datetime | None,
        Field(default=None, description="When task finished (success or failure)"),
    ]
    duration_ms: Annotated[
        int | None,
        Field(default=None, ge=0, description="Execution time in milliseconds"),
    ]

    # Execution Context
    worker_id: Annotated[
        str | None,
        Field(default=None, description="Worker ID processing this task"),
    ]
    attempt: Annotated[
        int,
        Field(default=1, ge=1, description="Current retry attempt number"),
    ]
    max_retries: Annotated[
        int,
        Field(default=3, ge=0, description="Maximum retry attempts allowed"),
    ]

    # Task Data
    args: Annotated[
        list[Any],
        Field(default_factory=list, description="Positional arguments"),
    ]
    kwargs: Annotated[
        dict[str, Any],
        Field(default_factory=dict, description="Keyword arguments"),
    ]

    # Result/Error
    result: Annotated[
        Any | None,
        Field(default=None, description="Task return value (if successful)"),
    ]
    exception: Annotated[
        str | None,
        Field(default=None, description="Exception message (if failed)"),
    ]
    traceback: Annotated[
        str | None,
        Field(default=None, description="Full exception traceback"),
    ]

    # Metadata
    priority: Annotated[
        int,
        Field(default=0, description="Task priority (higher = more important)"),
    ]
    timeout_seconds: Annotated[
        int | None,
        Field(default=None, ge=1, description="Execution timeout in seconds"),
    ]
    tags: Annotated[
        list[str],
        Field(default_factory=list, description="Custom tags for filtering"),
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_retryable(self) -> bool:
        """Check if this task can be retried."""
        return self.status == TaskStatus.FAILED and self.attempt < self.max_retries

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_error(self) -> bool:
        """Check if this task has an error (failed or has exception)."""
        return self.status == TaskStatus.FAILED or self.exception is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_seconds(self) -> float | None:
        """Get execution duration in seconds (or None if not available)."""
        if self.duration_ms is not None:
            return self.duration_ms / 1000.0
        return None

    @classmethod
    def from_task_info(cls, task_info: TaskInfo) -> Self:
        """Convert core TaskInfo dataclass to rich Pydantic Task model.

        Args:
            task_info: TaskInfo dataclass from the core driver.

        Returns:
            Task model with all fields populated.
        """
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
    """Filters for task list queries.

    All fields are optional - only provided filters are applied.
    """

    model_config = ConfigDict(
        # Don't fail on extra fields in requests
        extra="ignore",
    )

    status: TaskStatus | None = Field(default=None, description="Filter by task status")
    queue: str | None = Field(default=None, description="Filter by queue name")
    worker_id: str | None = Field(default=None, description="Filter by worker ID")
    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Search in task name, ID, or arguments",
    )
    from_date: datetime | None = Field(default=None, description="Filter tasks created after")
    to_date: datetime | None = Field(default=None, description="Filter tasks created before")
    tags: list[str] | None = Field(default=None, description="Filter by tags (any match)")

    @field_validator("search", mode="before")
    @classmethod
    def strip_search(cls, v: str | None) -> str | None:
        """Strip whitespace from search query."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class TaskListResponse(BaseModel):
    """Paginated response for task list endpoints.

    Follows REST best practices with items, total count, and pagination info.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 0,
                "limit": 50,
                "offset": 0,
            },
        },
    )

    items: Annotated[list[Task], Field(description="List of tasks for this page")]
    total: Annotated[int, Field(ge=0, description="Total number of tasks matching filters")]
    limit: Annotated[int, Field(default=50, ge=1, le=500, description="Items per page")]
    offset: Annotated[int, Field(default=0, ge=0, description="Pagination offset")]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_more(self) -> bool:
        """Check if there are more pages available."""
        return self.offset + len(self.items) < self.total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def page(self) -> int:
        """Get current page number (1-indexed)."""
        return (self.offset // self.limit) + 1 if self.limit > 0 else 1

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        if self.limit <= 0:
            return 1
        return (self.total + self.limit - 1) // self.limit
