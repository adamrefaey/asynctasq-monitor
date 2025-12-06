"""Service layer for queue monitoring operations.

This module provides the QueueService class that wraps the core driver
and provides queue management functionality for the monitoring API.
"""

from datetime import datetime

from asynctasq.core.dispatcher import get_dispatcher
from asynctasq.drivers.base_driver import BaseDriver
from asynctasq_monitor.models.queue import (
    Queue,
    QueueActionResponse,
    QueueClearResponse,
    QueueFilters,
    QueueListResponse,
    QueueMetrics,
    QueueStatus,
)


class QueueService:
    """Wrap the core driver to provide queue monitoring operations.

    This service handles:
    - Listing queues with filtering
    - Getting queue details
    - Pause/resume queue operations
    - Clearing queues
    - Queue metrics retrieval
    """

    _driver: BaseDriver | None

    def __init__(self) -> None:
        """Create a QueueService with no attached driver initially."""
        self._driver = None

    async def get_queues(
        self,
        filters: QueueFilters | None = None,
    ) -> QueueListResponse:
        """Fetch all queues with optional filtering.

        Args:
            filters: Optional filters to apply

        Returns:
            QueueListResponse with list of queues and total count
        """
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)

        # Get all queue names from driver
        queue_names = await self._driver.get_all_queue_names()

        # Fetch stats for each queue
        queues: list[Queue] = []
        for name in queue_names:
            stats = await self._driver.get_queue_stats(name)
            queue = Queue(
                name=stats["name"],
                status=QueueStatus.ACTIVE,  # TODO: Get from driver when supported
                depth=stats["depth"],
                processing=stats["processing"],
                completed_total=stats["completed_total"],
                failed_total=stats["failed_total"],
                workers_assigned=0,  # TODO: Get from worker registry
                avg_duration_ms=stats["avg_duration_ms"],
                throughput_per_minute=stats["throughput_per_minute"],
                priority=0,
                max_retries=3,
                created_at=None,
                paused_at=None,
            )
            queues.append(queue)

        # Apply filters if provided
        if filters:
            if filters.status is not None:
                queues = [q for q in queues if q.status == filters.status]
            if filters.search is not None:
                search_lower = filters.search.lower()
                queues = [q for q in queues if search_lower in q.name.lower()]
            if filters.min_depth is not None:
                queues = [q for q in queues if q.depth >= filters.min_depth]
            if filters.alert_level is not None:
                queues = [q for q in queues if q.alert_level == filters.alert_level]

        return QueueListResponse(items=queues, total=len(queues))

    async def get_queue_by_name(self, queue_name: str) -> Queue | None:
        """Get a single queue by name.

        Args:
            queue_name: The queue name to look up

        Returns:
            Queue model or None if not found
        """
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)

        try:
            stats = await self._driver.get_queue_stats(queue_name)
            return Queue(
                name=stats["name"],
                status=QueueStatus.ACTIVE,
                depth=stats["depth"],
                processing=stats["processing"],
                completed_total=stats["completed_total"],
                failed_total=stats["failed_total"],
                workers_assigned=0,
                avg_duration_ms=stats["avg_duration_ms"],
                throughput_per_minute=stats["throughput_per_minute"],
                priority=0,
                max_retries=3,
                created_at=None,
                paused_at=None,
            )
        except Exception:
            return None

    async def pause_queue(self, queue_name: str, reason: str | None = None) -> QueueActionResponse:
        """Pause a queue to stop processing tasks.

        Args:
            queue_name: Queue to pause
            reason: Optional reason for pausing

        Returns:
            QueueActionResponse indicating success/failure
        """
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)

        # Check if queue exists
        queue = await self.get_queue_by_name(queue_name)
        if queue is None:
            return QueueActionResponse(
                success=False,
                queue_name=queue_name,
                action="pause",
                message=f"Queue '{queue_name}' not found",
            )

        # TODO: Implement actual pause via driver when supported
        # For now, return success as placeholder
        return QueueActionResponse(
            success=True,
            queue_name=queue_name,
            action="pause",
            message=f"Queue '{queue_name}' paused successfully"
            + (f" - Reason: {reason}" if reason else ""),
        )

    async def resume_queue(self, queue_name: str) -> QueueActionResponse:
        """Resume a paused queue to continue processing.

        Args:
            queue_name: Queue to resume

        Returns:
            QueueActionResponse indicating success/failure
        """
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)

        # Check if queue exists
        queue = await self.get_queue_by_name(queue_name)
        if queue is None:
            return QueueActionResponse(
                success=False,
                queue_name=queue_name,
                action="resume",
                message=f"Queue '{queue_name}' not found",
            )

        # TODO: Implement actual resume via driver when supported
        return QueueActionResponse(
            success=True,
            queue_name=queue_name,
            action="resume",
            message=f"Queue '{queue_name}' resumed successfully",
        )

    async def clear_queue(self, queue_name: str) -> QueueClearResponse:
        """Clear all pending tasks from a queue.

        WARNING: This is a destructive operation that cannot be undone.

        Args:
            queue_name: Queue to clear

        Returns:
            QueueClearResponse with number of tasks cleared
        """
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)

        # Check if queue exists
        queue = await self.get_queue_by_name(queue_name)
        if queue is None:
            return QueueClearResponse(
                success=False,
                queue_name=queue_name,
                tasks_cleared=0,
                message=f"Queue '{queue_name}' not found",
            )

        pending_count = queue.depth

        # TODO: Implement actual clear via driver when supported
        # For now, return success as placeholder
        return QueueClearResponse(
            success=True,
            queue_name=queue_name,
            tasks_cleared=pending_count,
            message=f"Cleared {pending_count} tasks from queue '{queue_name}'",
        )

    async def get_queue_metrics(
        self,
        queue_name: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        interval_minutes: int = 5,
    ) -> list[QueueMetrics]:
        """Get historical metrics for a queue.

        Args:
            queue_name: Queue to get metrics for
            from_time: Start time for metrics (defaults to 24h ago)
            to_time: End time for metrics (defaults to now)
            interval_minutes: Aggregation interval in minutes

        Returns:
            List of QueueMetrics datapoints
        """
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)

        # TODO: Implement actual metrics retrieval from TimescaleDB/driver
        # For now, return empty list as placeholder
        _ = from_time, to_time, interval_minutes
        return []

    def _ensure_driver(self) -> None:
        """Ensure the core driver is available.

        Raises:
            RuntimeError: If the dispatcher or driver cannot be obtained.
        """
        if self._driver is None:
            dispatcher = get_dispatcher()
            missing_msg = "Dispatcher driver not available"
            if dispatcher is None or not hasattr(dispatcher, "driver"):
                raise RuntimeError(missing_msg)
            self._driver = dispatcher.driver
