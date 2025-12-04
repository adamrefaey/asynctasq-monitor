"""Models package for asynctasq_monitor.

This module re-exports the primary Pydantic models used by the API.
All models follow Pydantic v2 best practices.
"""

# Re-export queue models
from .queue import (
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

# Re-export task models for convenient imports
from .task import Task, TaskFilters, TaskListResponse, TaskStatus

# Re-export worker models
from .worker import (
    HeartbeatRequest,
    HeartbeatResponse,
    Worker,
    WorkerAction,
    WorkerActionRequest,
    WorkerActionResponse,
    WorkerDetail,
    WorkerFilters,
    WorkerListResponse,
    WorkerLog,
    WorkerLogsResponse,
    WorkerStatus,
    WorkerTask,
)

__all__ = [
    # Queue models
    "Queue",
    "QueueActionRequest",
    "QueueActionResponse",
    "QueueAlertLevel",
    "QueueClearResponse",
    "QueueFilters",
    "QueueListResponse",
    "QueueMetrics",
    "QueueStatus",
    # Task models
    "Task",
    "TaskFilters",
    "TaskListResponse",
    "TaskStatus",
    # Worker models
    "HeartbeatRequest",
    "HeartbeatResponse",
    "Worker",
    "WorkerAction",
    "WorkerActionRequest",
    "WorkerActionResponse",
    "WorkerDetail",
    "WorkerFilters",
    "WorkerListResponse",
    "WorkerLog",
    "WorkerLogsResponse",
    "WorkerStatus",
    "WorkerTask",
]
