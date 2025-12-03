"""Pydantic models for worker monitoring.

This module defines data models following Pydantic v2 best practices:
- Use ConfigDict for model configuration (not class-based Config)
- Use Field() with proper descriptions and constraints
- Use computed_field for derived properties
- Use model_validator for complex validation
- Use Annotated types for better documentation
"""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class WorkerStatus(str, Enum):
    """Worker status enum.

    Workers can be in one of three states:
    - active: Currently processing tasks
    - idle: Connected but not processing
    - offline: No heartbeat received recently
    """

    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"

    @property
    def is_online(self) -> bool:
        """Check if worker is reachable (active or idle)."""
        return self in {WorkerStatus.ACTIVE, WorkerStatus.IDLE}


class WorkerAction(str, Enum):
    """Actions that can be performed on a worker."""

    PAUSE = "pause"
    RESUME = "resume"
    SHUTDOWN = "shutdown"  # Graceful shutdown
    KILL = "kill"  # Immediate termination


class Worker(BaseModel):
    """Complete worker representation for monitoring.

    This model represents a task queue worker with all its metadata,
    resource usage, and current processing state.

    Example:
        >>> worker = Worker(
        ...     id="worker-001",
        ...     name="worker-prod-01",
        ...     hostname="server-01.example.com",
        ...     status=WorkerStatus.ACTIVE,
        ...     last_heartbeat=datetime.now(UTC),
        ... )
    """

    model_config = ConfigDict(
        # Validate data on assignment (not just construction)
        validate_assignment=True,
        # Use enum values in JSON output
        use_enum_values=True,
        # Allow coercion for API responses
        strict=False,
        # JSON schema example for OpenAPI docs
        json_schema_extra={
            "example": {
                "id": "worker-001",
                "name": "worker-prod-01",
                "hostname": "server-01.example.com",
                "pid": 12345,
                "status": "active",
                "queues": ["default", "high", "emails"],
                "current_task_id": "550e8400-e29b-41d4-a716-446655440000",
                "current_task_name": "send_email",
                "tasks_processed": 1542,
                "tasks_failed": 23,
                "uptime_seconds": 86400,
                "started_at": "2025-11-27T10:00:00Z",
                "last_heartbeat": "2025-11-28T10:00:00Z",
                "cpu_usage": 45.5,
                "memory_usage": 62.3,
                "memory_mb": 512,
                "is_paused": False,
            },
        },
    )

    # Identity
    id: Annotated[str, Field(description="Unique worker ID")]
    name: Annotated[str, Field(description="Worker display name (usually hostname)")]
    hostname: str | None = Field(default=None, description="Worker hostname")
    pid: int | None = Field(default=None, ge=1, description="Process ID on the host")

    # Status
    status: WorkerStatus
    is_paused: bool = Field(
        default=False, description="Whether worker is paused (not accepting new tasks)"
    )

    # Queues
    queues: list[str] = Field(
        default_factory=list, description="List of queues this worker is processing"
    )

    # Current Task
    current_task_id: str | None = Field(
        default=None, description="ID of task currently being processed"
    )
    current_task_name: str | None = Field(
        default=None, description="Name of task currently being processed"
    )
    current_task_started_at: datetime | None = Field(
        default=None, description="When current task started processing"
    )

    # Statistics
    tasks_processed: int = Field(default=0, ge=0, description="Total tasks successfully processed")
    tasks_failed: int = Field(default=0, ge=0, description="Total tasks that failed")
    avg_task_duration_ms: float | None = Field(
        default=None, ge=0, description="Average task duration in milliseconds"
    )

    # Timing
    uptime_seconds: int = Field(default=0, ge=0, description="Worker uptime in seconds")
    started_at: datetime | None = Field(default=None, description="When worker started")
    last_heartbeat: Annotated[datetime, Field(description="Last heartbeat timestamp")]

    # Resource Usage
    cpu_usage: float | None = Field(
        default=None, ge=0, le=100, description="CPU usage percentage (0-100)"
    )
    memory_usage: float | None = Field(
        default=None, ge=0, le=100, description="Memory usage percentage (0-100)"
    )
    memory_mb: int | None = Field(default=None, ge=0, description="Memory usage in megabytes")

    # Metadata
    version: str | None = Field(default=None, description="Worker software version")
    tags: list[str] = Field(default_factory=list, description="Custom tags for filtering")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_online(self) -> bool:
        """Check if worker is currently online (active or idle)."""
        return self.status != WorkerStatus.OFFLINE

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_processing(self) -> bool:
        """Check if worker is currently processing a task."""
        return self.current_task_id is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_rate(self) -> float:
        """Calculate task success rate as percentage."""
        total = self.tasks_processed + self.tasks_failed
        if total == 0:
            return 100.0
        return round((self.tasks_processed / total) * 100, 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tasks_per_hour(self) -> float:
        """Calculate average tasks processed per hour."""
        if self.uptime_seconds == 0:
            return 0.0
        hours = self.uptime_seconds / 3600
        if hours == 0:
            return 0.0
        return round(self.tasks_processed / hours, 2)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def uptime_formatted(self) -> str:
        """Get human-readable uptime string."""
        delta = timedelta(seconds=self.uptime_seconds)
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def seconds_since_heartbeat(self) -> int:
        """Seconds since last heartbeat (for freshness check)."""
        now = datetime.now(UTC)
        # Handle naive datetime by assuming UTC
        heartbeat = self.last_heartbeat
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=UTC)
        return int((now - heartbeat).total_seconds())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def load_percentage(self) -> float:
        """Calculate load percentage based on CPU and memory."""
        if self.cpu_usage is None and self.memory_usage is None:
            return 0.0
        cpu = self.cpu_usage or 0.0
        mem = self.memory_usage or 0.0
        # Weight CPU slightly higher than memory
        return round((cpu * 0.6 + mem * 0.4), 1)


class WorkerTask(BaseModel):
    """A task in worker's history."""

    model_config = ConfigDict(use_enum_values=True)

    id: Annotated[str, Field(description="Task ID")]
    name: Annotated[str, Field(description="Task function name")]
    queue: Annotated[str, Field(description="Queue name")]
    status: Annotated[str, Field(description="Task status")]
    started_at: Annotated[datetime, Field(description="When task started")]
    completed_at: Annotated[datetime | None, Field(default=None, description="When task finished")]
    duration_ms: Annotated[int | None, Field(default=None, ge=0, description="Duration in ms")]


class WorkerDetail(Worker):
    """Extended worker model with additional details for detail view.

    Inherits from Worker and adds:
    - Recent task history
    - Performance metrics over time
    - Log entries
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "worker-001",
                "name": "worker-prod-01",
                "hostname": "server-01.example.com",
                "pid": 12345,
                "status": "active",
                "queues": ["default", "high", "emails"],
                "recent_tasks": [],
                "hourly_throughput": [],
            },
        },
    )

    # Task History
    recent_tasks: list[WorkerTask] = Field(
        default_factory=list, description="Last 100 tasks processed by this worker"
    )

    # Performance over time (last 24 hours)
    hourly_throughput: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Hourly throughput data for charts (timestamp, count)",
    )


class WorkerLog(BaseModel):
    """A single log entry from a worker."""

    timestamp: Annotated[datetime, Field(description="When log was emitted")]
    level: Annotated[str, Field(description="Log level (DEBUG, INFO, WARNING, ERROR)")]
    message: Annotated[str, Field(description="Log message content")]
    logger_name: Annotated[str | None, Field(default=None, description="Logger name")]


class WorkerListResponse(BaseModel):
    """Paginated response for worker list endpoints."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 0,
            },
        },
    )

    items: Annotated[list[Worker], Field(description="List of workers")]
    total: Annotated[int, Field(ge=0, description="Total number of workers")]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def active_count(self) -> int:
        """Count of active workers."""
        return sum(1 for w in self.items if w.status == WorkerStatus.ACTIVE)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def idle_count(self) -> int:
        """Count of idle workers."""
        return sum(1 for w in self.items if w.status == WorkerStatus.IDLE)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def offline_count(self) -> int:
        """Count of offline workers."""
        return sum(1 for w in self.items if w.status == WorkerStatus.OFFLINE)


class WorkerFilters(BaseModel):
    """Filters for worker list queries."""

    model_config = ConfigDict(extra="ignore")

    status: WorkerStatus | None = Field(default=None, description="Filter by worker status")
    queue: str | None = Field(default=None, description="Filter by queue name")
    search: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Search in worker name, ID, or hostname",
    )
    is_paused: bool | None = Field(default=None, description="Filter by paused state")
    has_current_task: bool | None = Field(
        default=None, description="Filter workers currently processing"
    )


class WorkerActionRequest(BaseModel):
    """Request body for worker management actions."""

    action: WorkerAction = Field(description="Action to perform on the worker")
    force: bool = Field(default=False, description="Force the action (for kill, skip confirmation)")


class WorkerActionResponse(BaseModel):
    """Response for worker management actions."""

    success: bool = Field(description="Whether the action was successful")
    worker_id: str = Field(description="ID of the worker that was acted upon")
    action: WorkerAction = Field(description="Action that was performed")
    message: str = Field(description="Human-readable result message")


class WorkerLogsResponse(BaseModel):
    """Response for worker logs endpoint."""

    worker_id: str = Field(description="Worker ID")
    logs: list[WorkerLog] = Field(default_factory=list, description="Log entries")
    total: int = Field(ge=0, description="Total log entries available")
    has_more: bool = Field(default=False, description="Whether more logs are available")


class HeartbeatRequest(BaseModel):
    """Request body for worker heartbeat."""

    worker_id: str = Field(description="Worker ID sending heartbeat")
    status: WorkerStatus = Field(description="Current worker status")
    current_task_id: str | None = Field(default=None, description="Current task if any")
    current_task_name: str | None = Field(default=None, description="Current task name if any")
    cpu_usage: float | None = Field(default=None, ge=0, le=100, description="CPU usage %")
    memory_usage: float | None = Field(default=None, ge=0, le=100, description="Memory usage %")
    memory_mb: int | None = Field(default=None, ge=0, description="Memory in MB")
    tasks_processed: int = Field(default=0, ge=0, description="Total tasks processed")
    tasks_failed: int = Field(default=0, ge=0, description="Total tasks failed")

    @model_validator(mode="after")
    def validate_task_fields(self) -> Self:
        """Ensure task name is provided if task ID is provided."""
        if self.current_task_id is not None and self.current_task_name is None:
            msg = "current_task_name is required when current_task_id is provided"
            raise ValueError(msg)
        return self


class HeartbeatResponse(BaseModel):
    """Response for worker heartbeat."""

    received: bool = Field(default=True, description="Whether heartbeat was received")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Server timestamp when heartbeat was processed",
    )
    should_pause: bool = Field(
        default=False,
        description="Whether worker should pause (admin action pending)",
    )
    should_shutdown: bool = Field(
        default=False,
        description="Whether worker should gracefully shutdown",
    )
