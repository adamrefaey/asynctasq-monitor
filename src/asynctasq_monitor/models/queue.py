"""Pydantic models for queue monitoring.

This module defines data models following Pydantic v2 best practices:
- Use ConfigDict for model configuration (not class-based Config)
- Use Field() with proper descriptions and constraints
- Use computed_field for derived properties
- Prefer strict mode where appropriate
"""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field


class QueueStatus(str, Enum):
    """Queue operational status.

    Enum values represent the current processing state of the queue.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"

    @property
    def is_processing(self) -> bool:
        """Check if the queue is actively processing tasks."""
        return self == QueueStatus.ACTIVE

    @property
    def accepts_new_tasks(self) -> bool:
        """Check if the queue accepts new task submissions."""
        return self in {QueueStatus.ACTIVE, QueueStatus.PAUSED}


class QueueAlertLevel(str, Enum):
    """Alert level based on queue depth thresholds."""

    NORMAL = "normal"
    WARNING = "warning"  # > 100 pending tasks
    CRITICAL = "critical"  # > 500 pending tasks


class Queue(BaseModel):
    """Complete queue representation for monitoring.

    This model represents a task queue with all its metadata and statistics.

    Example:
        >>> queue = Queue(
        ...     name="emails",
        ...     status=QueueStatus.ACTIVE,
        ...     depth=42,
        ...     processing=5,
        ... )
    """

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        strict=False,
        json_schema_extra={
            "example": {
                "name": "emails",
                "status": "active",
                "depth": 42,
                "processing": 5,
                "completed_total": 15000,
                "failed_total": 150,
                "workers_assigned": 3,
                "avg_duration_ms": 1250.5,
                "throughput_per_minute": 45.2,
                "priority": 1,
                "max_retries": 3,
                "created_at": "2025-01-01T00:00:00Z",
                "paused_at": None,
            },
        },
    )

    # Identity
    name: Annotated[str, Field(description="Unique queue name")]

    # Status
    status: QueueStatus = Field(
        default=QueueStatus.ACTIVE,
        description="Current queue operational status",
    )

    # Counts
    depth: Annotated[
        int,
        Field(default=0, ge=0, description="Number of pending tasks in queue"),
    ]
    processing: Annotated[
        int,
        Field(default=0, ge=0, description="Number of tasks currently being processed"),
    ]
    completed_total: Annotated[
        int,
        Field(default=0, ge=0, description="Total number of completed tasks"),
    ]
    failed_total: Annotated[
        int,
        Field(default=0, ge=0, description="Total number of failed tasks"),
    ]

    # Workers
    workers_assigned: Annotated[
        int,
        Field(default=0, ge=0, description="Number of workers assigned to this queue"),
    ]

    # Performance Metrics
    avg_duration_ms: Annotated[
        float | None,
        Field(default=None, ge=0, description="Average task duration in milliseconds"),
    ]
    throughput_per_minute: Annotated[
        float | None,
        Field(default=None, ge=0, description="Tasks processed per minute"),
    ]

    # Configuration
    priority: Annotated[
        int,
        Field(default=0, description="Queue priority (higher = more important)"),
    ]
    max_retries: Annotated[
        int,
        Field(default=3, ge=0, description="Default max retries for tasks in this queue"),
    ]

    # Timestamps
    created_at: Annotated[
        datetime | None,
        Field(default=None, description="When the queue was created"),
    ]
    paused_at: Annotated[
        datetime | None,
        Field(default=None, description="When the queue was paused (if paused)"),
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def alert_level(self) -> QueueAlertLevel:
        """Determine alert level based on queue depth thresholds."""
        if self.depth >= 500:
            return QueueAlertLevel.CRITICAL
        if self.depth >= 100:
            return QueueAlertLevel.WARNING
        return QueueAlertLevel.NORMAL

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tasks(self) -> int:
        """Get total tasks (pending + processing + completed + failed)."""
        return self.depth + self.processing + self.completed_total + self.failed_total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage (0-100)."""
        total = self.completed_total + self.failed_total
        if total == 0:
            return 100.0
        return (self.completed_total / total) * 100

    @computed_field  # type: ignore[prop-decorator]
    @property
    def avg_duration_seconds(self) -> float | None:
        """Get average duration in seconds (or None if not available)."""
        if self.avg_duration_ms is not None:
            return self.avg_duration_ms / 1000.0
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_idle(self) -> bool:
        """Check if queue has no pending or processing tasks."""
        return self.depth == 0 and self.processing == 0


class QueueMetrics(BaseModel):
    """Historical metrics for a queue over time.

    Used for charts and trend analysis.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queue_name": "emails",
                "timestamp": "2025-12-04T10:00:00Z",
                "depth": 42,
                "throughput": 45.2,
                "avg_duration_ms": 1250.5,
                "error_rate": 1.5,
            },
        },
    )

    queue_name: Annotated[str, Field(description="Queue name")]
    timestamp: Annotated[datetime, Field(description="Metric timestamp")]
    depth: Annotated[int, Field(ge=0, description="Queue depth at this time")]
    throughput: Annotated[
        float | None,
        Field(default=None, ge=0, description="Tasks per minute at this time"),
    ]
    avg_duration_ms: Annotated[
        float | None,
        Field(default=None, ge=0, description="Average duration at this time"),
    ]
    error_rate: Annotated[
        float | None,
        Field(default=None, ge=0, le=100, description="Error rate percentage"),
    ]


class QueueFilters(BaseModel):
    """Filters for queue list queries.

    All fields are optional - only provided filters are applied.
    """

    model_config = ConfigDict(extra="ignore")

    status: QueueStatus | None = Field(default=None, description="Filter by queue status")
    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Search in queue name",
    )
    min_depth: int | None = Field(
        default=None,
        ge=0,
        description="Filter queues with depth >= this value",
    )
    alert_level: QueueAlertLevel | None = Field(
        default=None,
        description="Filter by alert level",
    )


class QueueListResponse(BaseModel):
    """Response for queue list endpoints.

    Follows REST best practices with items and total count.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 0,
            },
        },
    )

    items: Annotated[list[Queue], Field(description="List of queues")]
    total: Annotated[int, Field(ge=0, description="Total number of queues")]


class QueueActionRequest(BaseModel):
    """Request body for queue actions (pause/resume)."""

    model_config = ConfigDict(extra="ignore")

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Optional reason for the action",
    )


class QueueActionResponse(BaseModel):
    """Response from queue action endpoints."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "queue_name": "emails",
                "action": "pause",
                "message": "Queue emails paused successfully",
            },
        },
    )

    success: Annotated[bool, Field(description="Whether the action was successful")]
    queue_name: Annotated[str, Field(description="Queue name the action was performed on")]
    action: Annotated[str, Field(description="Action that was performed")]
    message: Annotated[str, Field(description="Human-readable result message")]


class QueueClearResponse(BaseModel):
    """Response from queue clear endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "queue_name": "emails",
                "tasks_cleared": 42,
                "message": "Cleared 42 tasks from queue emails",
            },
        },
    )

    success: Annotated[bool, Field(description="Whether the clear was successful")]
    queue_name: Annotated[str, Field(description="Queue name that was cleared")]
    tasks_cleared: Annotated[int, Field(ge=0, description="Number of tasks cleared")]
    message: Annotated[str, Field(description="Human-readable result message")]
