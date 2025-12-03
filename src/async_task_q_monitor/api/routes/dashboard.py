"""Dashboard routes for the monitoring UI.

Provides summary statistics and health check endpoints.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, computed_field

from async_task_q_monitor.api.dependencies import TaskServiceDep
from async_task_q_monitor.models.task import TaskFilters, TaskStatus

router = APIRouter(tags=["dashboard"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class StatusCount(BaseModel):
    """Count of tasks in a particular status."""

    model_config = ConfigDict(frozen=True)

    status: TaskStatus
    count: Annotated[int, Field(ge=0)]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def label(self) -> str:
        """Human-readable label for this status."""
        return self.status.value.capitalize()


class QueueStats(BaseModel):
    """Statistics for a single queue."""

    model_config = ConfigDict(frozen=True)

    name: Annotated[str, Field(description="Queue name")]
    pending: Annotated[int, Field(ge=0, description="Number of pending tasks")]
    running: Annotated[int, Field(ge=0, description="Number of running tasks")]
    failed: Annotated[int, Field(ge=0, description="Number of failed tasks")]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        """Total tasks in this queue (pending + running + failed)."""
        return self.pending + self.running + self.failed


class DashboardSummary(BaseModel):
    """Complete dashboard summary response.

    Contains task counts by status and queue-level statistics.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_tasks": 150,
                "by_status": [
                    {"status": "pending", "count": 50, "label": "Pending"},
                    {"status": "running", "count": 10, "label": "Running"},
                    {"status": "completed", "count": 80, "label": "Completed"},
                    {"status": "failed", "count": 10, "label": "Failed"},
                ],
                "queues": [
                    {"name": "default", "pending": 30, "running": 5, "failed": 3, "total": 38},
                    {"name": "emails", "pending": 20, "running": 5, "failed": 7, "total": 32},
                ],
                "active_workers": 3,
                "success_rate": 88.89,
                "updated_at": "2025-11-28T10:00:00Z",
            },
        },
    )

    total_tasks: Annotated[int, Field(ge=0, description="Total number of tasks")]
    by_status: Annotated[list[StatusCount], Field(description="Task counts by status")]
    queues: Annotated[list[QueueStats], Field(description="Per-queue statistics")]
    active_workers: Annotated[int, Field(ge=0, description="Number of active workers")]
    success_rate: Annotated[float, Field(ge=0, le=100, description="Success rate percentage")]
    updated_at: Annotated[datetime, Field(description="When this summary was generated")]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pending_count(self) -> int:
        """Total pending tasks across all queues."""
        return next(
            (s.count for s in self.by_status if s.status == TaskStatus.PENDING),
            0,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_count(self) -> int:
        """Total failed tasks across all queues."""
        return next(
            (s.count for s in self.by_status if s.status == TaskStatus.FAILED),
            0,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def running_count(self) -> int:
        """Total running tasks across all queues."""
        return next(
            (s.count for s in self.by_status if s.status == TaskStatus.RUNNING),
            0,
        )


class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(frozen=True)

    status: Annotated[str, Field(description="Service health status")]
    service: Annotated[str, Field(description="Service name")]
    version: Annotated[str, Field(description="API version")]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/")
async def dashboard_root() -> HealthResponse:
    """Root dashboard health endpoint.

    Use this for health checks and service discovery.
    """
    return HealthResponse(
        status="ok",
        service="async-task-q-monitor",
        version="1.0.0",
    )


@router.get("/dashboard/summary")
async def get_summary(
    task_service: TaskServiceDep,
) -> DashboardSummary:
    """Return dashboard summary with task statistics.

    Provides:
    - Total task count
    - Tasks grouped by status
    - Per-queue statistics
    - Active worker count
    - Overall success rate
    """
    # Collect counts by status
    status_counts: list[StatusCount] = []
    total = 0

    for status in TaskStatus:
        filters = TaskFilters(status=status)
        _, count = await task_service.get_tasks(filters, limit=1, offset=0)
        status_counts.append(StatusCount(status=status, count=count))
        total += count

    # Calculate success rate
    completed = next(
        (s.count for s in status_counts if s.status == TaskStatus.COMPLETED),
        0,
    )
    failed = next(
        (s.count for s in status_counts if s.status == TaskStatus.FAILED),
        0,
    )
    finished = completed + failed
    success_rate = (completed / finished * 100) if finished > 0 else 100.0

    # For now, queue stats are simplified - could be enhanced with driver support
    # This is a placeholder until we have queue-specific queries
    queues: list[QueueStats] = []

    # Active workers count - placeholder until worker tracking is implemented
    active_workers = 0

    return DashboardSummary(
        total_tasks=total,
        by_status=status_counts,
        queues=queues,
        active_workers=active_workers,
        success_rate=round(success_rate, 2),
        updated_at=datetime.now(UTC),
    )
