"""Event broadcasting service for task queue events.

This module provides a centralized service for broadcasting task queue events
to WebSocket clients. It integrates with the ConnectionManager and handles
routing events to the appropriate rooms.

Following best practices:
- Type-safe event handling with Pydantic models
- Efficient room-based broadcasting
- Clean async/await patterns
"""

import logging
from typing import TYPE_CHECKING

from asynctasq_monitor.websocket.events import (
    QueueEvent,
    TaskEvent,
    WebSocketEventType,
    WorkerEvent,
)
from asynctasq_monitor.websocket.manager import get_connection_manager

if TYPE_CHECKING:
    from asynctasq_monitor.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """Service for broadcasting task queue events to WebSocket clients.

    This service provides methods for broadcasting different types of events
    to the appropriate WebSocket rooms:

    - Task events → `global`, `tasks`, `task:{id}`, `queue:{name}`
    - Worker events → `global`, `workers`, `worker:{id}`
    - Queue events → `global`, `queues`, `queue:{name}`

    Example:
        >>> broadcaster = EventBroadcaster()
        >>> await broadcaster.broadcast_task_completed(
        ...     task_id="abc123",
        ...     task_name="send_email",
        ...     queue="emails",
        ...     worker_id="worker-1",
        ...     duration_ms=2150,
        ... )
    """

    def __init__(self, connection_manager: "ConnectionManager | None" = None) -> None:
        """Initialize the event broadcaster.

        Args:
            connection_manager: WebSocket connection manager. If None, uses
                               the global singleton.
        """
        self._manager = connection_manager

    @property
    def manager(self) -> "ConnectionManager":
        """Get the connection manager, lazily initializing if needed."""
        if self._manager is None:
            self._manager = get_connection_manager()
        return self._manager

    # -------------------------------------------------------------------------
    # Task Events
    # -------------------------------------------------------------------------

    async def broadcast_task_enqueued(
        self,
        task_id: str,
        task_name: str,
        queue: str,
        *,
        priority: int = 0,
    ) -> int:
        """Broadcast a task enqueued event.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task function
            queue: Queue name the task was added to
            priority: Task priority

        Returns:
            Number of clients that received the event
        """
        event = TaskEvent(
            type=WebSocketEventType.TASK_ENQUEUED,
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            status="pending",
        )

        rooms = ["global", "tasks", f"queue:{queue}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_task_started(
        self,
        task_id: str,
        task_name: str,
        queue: str,
        worker_id: str,
        *,
        attempt: int = 1,
    ) -> int:
        """Broadcast a task started event.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task function
            queue: Queue name
            worker_id: Worker processing the task
            attempt: Current retry attempt number

        Returns:
            Number of clients that received the event
        """
        event = TaskEvent(
            type=WebSocketEventType.TASK_STARTED,
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            worker_id=worker_id,
            status="running",
            attempt=attempt,
        )

        rooms = ["global", "tasks", f"task:{task_id}", f"queue:{queue}", f"worker:{worker_id}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_task_completed(
        self,
        task_id: str,
        task_name: str,
        queue: str,
        *,
        worker_id: str | None = None,
        duration_ms: int | None = None,
    ) -> int:
        """Broadcast a task completed event.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task function
            queue: Queue name
            worker_id: Worker that processed the task
            duration_ms: Execution duration in milliseconds

        Returns:
            Number of clients that received the event
        """
        event = TaskEvent(
            type=WebSocketEventType.TASK_COMPLETED,
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            worker_id=worker_id,
            status="completed",
            duration_ms=duration_ms,
        )

        rooms = ["global", "tasks", f"task:{task_id}", f"queue:{queue}"]
        if worker_id:
            rooms.append(f"worker:{worker_id}")

        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_task_failed(
        self,
        task_id: str,
        task_name: str,
        queue: str,
        *,
        worker_id: str | None = None,
        error: str | None = None,
        attempt: int = 1,
        duration_ms: int | None = None,
    ) -> int:
        """Broadcast a task failed event.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task function
            queue: Queue name
            worker_id: Worker that processed the task
            error: Error message
            attempt: Current retry attempt number
            duration_ms: Execution duration in milliseconds

        Returns:
            Number of clients that received the event
        """
        event = TaskEvent(
            type=WebSocketEventType.TASK_FAILED,
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            worker_id=worker_id,
            status="failed",
            error=error,
            attempt=attempt,
            duration_ms=duration_ms,
        )

        rooms = ["global", "tasks", f"task:{task_id}", f"queue:{queue}"]
        if worker_id:
            rooms.append(f"worker:{worker_id}")

        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_task_retrying(
        self,
        task_id: str,
        task_name: str,
        queue: str,
        *,
        attempt: int,
        error: str | None = None,
    ) -> int:
        """Broadcast a task retrying event.

        Args:
            task_id: Unique task identifier
            task_name: Name of the task function
            queue: Queue name
            attempt: Current retry attempt number
            error: Error from previous attempt

        Returns:
            Number of clients that received the event
        """
        event = TaskEvent(
            type=WebSocketEventType.TASK_RETRYING,
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            status="retrying",
            attempt=attempt,
            error=error,
        )

        rooms = ["global", "tasks", f"task:{task_id}", f"queue:{queue}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    # -------------------------------------------------------------------------
    # Worker Events
    # -------------------------------------------------------------------------

    async def broadcast_worker_started(
        self,
        worker_id: str,
    ) -> int:
        """Broadcast a worker started event.

        Args:
            worker_id: Unique worker identifier

        Returns:
            Number of clients that received the event
        """
        event = WorkerEvent(
            type=WebSocketEventType.WORKER_STARTED,
            worker_id=worker_id,
            status="active",
        )

        rooms = ["global", "workers", f"worker:{worker_id}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_worker_stopped(
        self,
        worker_id: str,
        *,
        tasks_processed: int | None = None,
        uptime_seconds: int | None = None,
    ) -> int:
        """Broadcast a worker stopped event.

        Args:
            worker_id: Unique worker identifier
            tasks_processed: Total tasks processed by worker
            uptime_seconds: How long the worker was running

        Returns:
            Number of clients that received the event
        """
        event = WorkerEvent(
            type=WebSocketEventType.WORKER_STOPPED,
            worker_id=worker_id,
            status="down",
            tasks_processed=tasks_processed,
            uptime_seconds=uptime_seconds,
        )

        rooms = ["global", "workers", f"worker:{worker_id}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_worker_heartbeat(
        self,
        worker_id: str,
        *,
        load_percentage: float | None = None,
        current_task_id: str | None = None,
        tasks_processed: int | None = None,
        uptime_seconds: int | None = None,
    ) -> int:
        """Broadcast a worker heartbeat event.

        Args:
            worker_id: Unique worker identifier
            load_percentage: Current worker load (0-100%)
            current_task_id: Task currently being processed
            tasks_processed: Total tasks processed
            uptime_seconds: Worker uptime

        Returns:
            Number of clients that received the event
        """
        event = WorkerEvent(
            type=WebSocketEventType.WORKER_HEARTBEAT,
            worker_id=worker_id,
            status="active",
            load_percentage=load_percentage,
            current_task_id=current_task_id,
            tasks_processed=tasks_processed,
            uptime_seconds=uptime_seconds,
        )

        rooms = ["workers", f"worker:{worker_id}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    # -------------------------------------------------------------------------
    # Queue Events
    # -------------------------------------------------------------------------

    async def broadcast_queue_depth_changed(
        self,
        queue_name: str,
        depth: int,
        *,
        processing: int | None = None,
        throughput_per_minute: float | None = None,
    ) -> int:
        """Broadcast a queue depth changed event.

        Args:
            queue_name: Queue name
            depth: Number of pending tasks
            processing: Number of tasks being processed
            throughput_per_minute: Tasks processed per minute

        Returns:
            Number of clients that received the event
        """
        event = QueueEvent(
            type=WebSocketEventType.QUEUE_DEPTH_CHANGED,
            queue_name=queue_name,
            depth=depth,
            processing=processing,
            throughput_per_minute=throughput_per_minute,
        )

        rooms = ["global", "queues", f"queue:{queue_name}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_queue_paused(
        self,
        queue_name: str,
    ) -> int:
        """Broadcast a queue paused event.

        Args:
            queue_name: Queue name

        Returns:
            Number of clients that received the event
        """
        event = QueueEvent(
            type=WebSocketEventType.QUEUE_PAUSED,
            queue_name=queue_name,
        )

        rooms = ["global", "queues", f"queue:{queue_name}"]
        return await self.manager.broadcast_to_rooms(rooms, event)

    async def broadcast_queue_resumed(
        self,
        queue_name: str,
    ) -> int:
        """Broadcast a queue resumed event.

        Args:
            queue_name: Queue name

        Returns:
            Number of clients that received the event
        """
        event = QueueEvent(
            type=WebSocketEventType.QUEUE_RESUMED,
            queue_name=queue_name,
        )

        rooms = ["global", "queues", f"queue:{queue_name}"]
        return await self.manager.broadcast_to_rooms(rooms, event)


# Global singleton instance
_broadcaster: EventBroadcaster | None = None


def get_event_broadcaster() -> EventBroadcaster:
    """Get or create the global EventBroadcaster singleton.

    Returns:
        The global EventBroadcaster instance
    """
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = EventBroadcaster()
    return _broadcaster


def set_event_broadcaster(broadcaster: EventBroadcaster | None) -> None:
    """Set the global EventBroadcaster instance (for testing).

    Args:
        broadcaster: The EventBroadcaster to use, or None to reset
    """
    global _broadcaster
    _broadcaster = broadcaster
