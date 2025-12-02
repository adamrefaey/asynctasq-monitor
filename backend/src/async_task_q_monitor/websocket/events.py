"""WebSocket event models for real-time monitoring.

This module defines strongly-typed event models using Pydantic v2 best practices:
- Use `model_config = ConfigDict(...)` instead of inner `Config` class
- Use `Field()` with descriptions for OpenAPI documentation
- Use discriminated unions for type-safe event handling
- Use `model_dump(mode="json")` for JSON serialization
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class WebSocketEventType(str, Enum):
    """Types of WebSocket events broadcast by the monitoring system."""

    # Task events
    TASK_ENQUEUED = "task_enqueued"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRYING = "task_retrying"
    TASK_CANCELLED = "task_cancelled"

    # Worker events
    WORKER_STARTED = "worker_started"
    WORKER_STOPPED = "worker_stopped"
    WORKER_HEARTBEAT = "worker_heartbeat"
    WORKER_LOAD_UPDATED = "worker_load_updated"

    # Queue events
    QUEUE_DEPTH_CHANGED = "queue_depth_changed"
    QUEUE_PAUSED = "queue_paused"
    QUEUE_RESUMED = "queue_resumed"

    # Metrics events
    METRICS_UPDATED = "metrics_updated"


def _utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


class BaseWebSocketEvent(BaseModel):
    """Base model for all WebSocket events.

    Following Pydantic v2 best practices:
    - ConfigDict for configuration
    - Field descriptions for OpenAPI
    - Frozen for immutability
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "description": "Base WebSocket event with timestamp",
        },
    )

    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when the event was created",
    )


class TaskEvent(BaseWebSocketEvent):
    """Event for task-related updates.

    Broadcast to rooms: `global`, `tasks`, `task:{id}`, `queue:{name}`
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "task_completed",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_name": "send_email",
                "queue": "emails",
                "worker_id": "worker-1",
                "duration_ms": 2150,
                "timestamp": "2025-12-02T10:00:07Z",
            },
        },
    )

    type: Literal[
        WebSocketEventType.TASK_ENQUEUED,
        WebSocketEventType.TASK_STARTED,
        WebSocketEventType.TASK_COMPLETED,
        WebSocketEventType.TASK_FAILED,
        WebSocketEventType.TASK_RETRYING,
        WebSocketEventType.TASK_CANCELLED,
    ] = Field(..., description="Type of task event")

    task_id: str = Field(..., description="Unique task identifier (UUID)")
    task_name: str = Field(..., description="Name of the task function")
    queue: str = Field(..., description="Queue name the task belongs to")
    worker_id: str | None = Field(default=None, description="Worker processing this task")
    status: str | None = Field(default=None, description="Current task status")
    duration_ms: int | None = Field(default=None, description="Execution duration in milliseconds")
    error: str | None = Field(default=None, description="Error message if task failed")
    attempt: int = Field(default=1, description="Current retry attempt number")


class WorkerEvent(BaseWebSocketEvent):
    """Event for worker-related updates.

    Broadcast to rooms: `global`, `workers`, `worker:{id}`
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "worker_heartbeat",
                "worker_id": "worker-1",
                "load_percentage": 75.5,
                "current_task_id": "550e8400-e29b-41d4-a716-446655440000",
                "tasks_processed": 1234,
                "timestamp": "2025-12-02T10:00:07Z",
            },
        },
    )

    type: Literal[
        WebSocketEventType.WORKER_STARTED,
        WebSocketEventType.WORKER_STOPPED,
        WebSocketEventType.WORKER_HEARTBEAT,
        WebSocketEventType.WORKER_LOAD_UPDATED,
    ] = Field(..., description="Type of worker event")

    worker_id: str = Field(..., description="Unique worker identifier")
    status: str | None = Field(default=None, description="Worker status (active, idle, down)")
    load_percentage: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Current worker load (0-100%)",
    )
    current_task_id: str | None = Field(default=None, description="Task currently being processed")
    tasks_processed: int | None = Field(default=None, description="Total tasks processed by worker")
    uptime_seconds: int | None = Field(default=None, description="Worker uptime in seconds")


class QueueEvent(BaseWebSocketEvent):
    """Event for queue-related updates.

    Broadcast to rooms: `global`, `queues`, `queue:{name}`
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "queue_depth_changed",
                "queue_name": "emails",
                "depth": 150,
                "processing": 5,
                "throughput_per_minute": 45.2,
                "timestamp": "2025-12-02T10:00:07Z",
            },
        },
    )

    type: Literal[
        WebSocketEventType.QUEUE_DEPTH_CHANGED,
        WebSocketEventType.QUEUE_PAUSED,
        WebSocketEventType.QUEUE_RESUMED,
    ] = Field(..., description="Type of queue event")

    queue_name: str = Field(..., description="Queue name")
    depth: int | None = Field(default=None, ge=0, description="Number of pending tasks")
    processing: int | None = Field(
        default=None, ge=0, description="Number of tasks being processed"
    )
    throughput_per_minute: float | None = Field(
        default=None,
        ge=0,
        description="Tasks processed per minute",
    )


class MetricsEvent(BaseWebSocketEvent):
    """Event for global metrics updates.

    Broadcast to rooms: `global`
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "metrics_updated",
                "pending": 150,
                "running": 5,
                "completed": 10243,
                "failed": 87,
                "success_rate": 99.15,
                "timestamp": "2025-12-02T10:00:07Z",
            },
        },
    )

    type: Literal[WebSocketEventType.METRICS_UPDATED] = Field(
        default=WebSocketEventType.METRICS_UPDATED,
        description="Metrics event type",
    )

    pending: int = Field(default=0, ge=0, description="Total pending tasks across all queues")
    running: int = Field(default=0, ge=0, description="Total running tasks")
    completed: int = Field(default=0, ge=0, description="Total completed tasks")
    failed: int = Field(default=0, ge=0, description="Total failed tasks")
    success_rate: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Success rate percentage",
    )
    active_workers: int = Field(default=0, ge=0, description="Number of active workers")
    queue_depths: dict[str, int] = Field(
        default_factory=dict,
        description="Depth per queue",
    )


# Discriminated union for type-safe event handling
WebSocketEvent = Annotated[
    TaskEvent | WorkerEvent | QueueEvent | MetricsEvent,
    Field(discriminator="type"),
]
