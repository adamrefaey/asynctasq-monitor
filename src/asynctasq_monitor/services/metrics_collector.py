"""Metrics collection service for real-time monitoring.

This module implements a background metrics collector that:
- Polls task queue drivers at configurable intervals
- Aggregates metrics (queue depth, task counts, worker stats)
- Broadcasts updates to WebSocket rooms
- Handles graceful startup/shutdown

Following Python best practices:
- Type hints throughout
- Proper async context management
- Structured logging
- Clean separation of concerns
"""

import asyncio
import contextlib
from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from asynctasq_monitor.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Background service for collecting and broadcasting metrics.

    This collector periodically polls the task queue driver for statistics
    and broadcasts updates to connected WebSocket clients.

    Attributes:
        poll_interval: How often to poll for metrics (seconds)
        _task: Background asyncio task
        _stop_event: Event to signal shutdown
        _manager: WebSocket connection manager

    Example:
        >>> collector = MetricsCollector(poll_interval=5.0)
        >>> await collector.start()
        >>> # ... later ...
        >>> await collector.stop()
    """

    DEFAULT_POLL_INTERVAL: float = 5.0

    def __init__(
        self,
        poll_interval: float | None = None,
        connection_manager: "ConnectionManager | None" = None,
    ) -> None:
        """Initialize the metrics collector.

        Args:
            poll_interval: How often to poll for metrics (seconds).
                          Defaults to 5.0 seconds.
            connection_manager: WebSocket connection manager for broadcasting.
                               If None, imports the global singleton.
        """
        self.poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._manager: ConnectionManager | None = connection_manager
        self._last_metrics: dict[str, Any] = {}

    @property
    def is_running(self) -> bool:
        """Check if the collector is currently running."""
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the background metrics collection task.

        This method is idempotent - calling it when already running has no effect.
        """
        if self.is_running:
            logger.warning("MetricsCollector already running")
            return

        self._stop_event.clear()

        # Lazily import connection manager if not provided
        if self._manager is None:
            try:
                from asynctasq_monitor.websocket.manager import get_connection_manager

                self._manager = get_connection_manager()
            except ImportError:
                logger.warning("WebSocket manager not available, running without broadcasts")

        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run(), name="metrics_collector")
        logger.info("MetricsCollector started with poll_interval=%.1fs", self.poll_interval)

    async def stop(self) -> None:
        """Stop the background metrics collection task.

        Waits for the current poll cycle to complete before returning.
        """
        if not self.is_running:
            return

        logger.info("Stopping MetricsCollector...")
        self._stop_event.set()

        if self._task:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        logger.info("MetricsCollector stopped")

    async def _run(self) -> None:
        """Main collection loop - runs until stop() is called."""
        logger.debug("MetricsCollector loop started")

        while not self._stop_event.is_set():
            try:
                await self._collect_and_broadcast()
            except Exception:
                logger.exception("Error in metrics collection cycle")

            # Wait for next poll interval or stop signal
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval,
                )
                # If we get here, stop was requested
                break
            except TimeoutError:
                # Normal timeout, continue polling
                continue

        logger.debug("MetricsCollector loop ended")

    async def _collect_and_broadcast(self) -> None:
        """Collect metrics from driver and broadcast to WebSocket clients."""
        metrics = await self._collect_metrics()

        if metrics and self._manager:
            await self._broadcast_metrics(metrics)

    async def _collect_metrics(self) -> dict[str, Any] | None:
        """Collect metrics from the task queue driver.

        Returns:
            Dictionary of metrics, or None if driver not available.
        """
        try:
            # Try to get the driver from the dispatcher
            from asynctasq.core.dispatcher import get_dispatcher

            dispatcher = get_dispatcher()
            if dispatcher is None or not hasattr(dispatcher, "driver"):
                logger.debug("Dispatcher or driver not available")
                return None

            driver = dispatcher.driver

            # Collect global stats
            global_stats = await driver.get_global_stats()

            # Collect queue stats
            queue_names = await driver.get_all_queue_names()
            queue_depths: dict[str, int] = {}
            for queue_name in queue_names:
                try:
                    queue_stats = await driver.get_queue_stats(queue_name)
                    queue_depths[queue_name] = queue_stats["depth"]
                except Exception:
                    logger.debug("Could not get stats for queue: %s", queue_name)

            # Collect worker stats
            worker_stats = await driver.get_worker_stats()
            active_workers = sum(1 for w in worker_stats if w["status"] == "active")

            # Calculate success rate
            total_completed = global_stats.get("completed", 0) + global_stats.get("failed", 0)
            success_rate = (
                (global_stats.get("completed", 0) / total_completed * 100)
                if total_completed > 0
                else 100.0
            )

            metrics = {
                "pending": global_stats.get("pending", 0),
                "running": global_stats.get("running", 0),
                "completed": global_stats.get("completed", 0),
                "failed": global_stats.get("failed", 0),
                "success_rate": round(success_rate, 2),
                "active_workers": active_workers,
                "queue_depths": queue_depths,
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }

            self._last_metrics = metrics
            return metrics

        except ImportError:
            logger.debug("asynctasq not available, returning stub metrics")
            return self._get_stub_metrics()

        except Exception:
            logger.exception("Error collecting metrics")
            return None

    def _get_stub_metrics(self) -> dict[str, Any]:
        """Return stub metrics when driver is not available (for testing)."""
        return {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "success_rate": 100.0,
            "active_workers": 0,
            "queue_depths": {},
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

    async def _broadcast_metrics(self, metrics: dict[str, Any]) -> None:
        """Broadcast metrics to WebSocket rooms.

        Args:
            metrics: Metrics dictionary to broadcast
        """
        if not self._manager:
            return

        # Import event type here to avoid circular imports
        from asynctasq_monitor.websocket.events import (
            MetricsEvent,
            QueueEvent,
            WebSocketEventType,
        )

        # Broadcast global metrics to 'global' room
        global_event = MetricsEvent(
            type=WebSocketEventType.METRICS_UPDATED,
            pending=metrics.get("pending", 0),
            running=metrics.get("running", 0),
            completed=metrics.get("completed", 0),
            failed=metrics.get("failed", 0),
            success_rate=metrics.get("success_rate"),
            active_workers=metrics.get("active_workers", 0),
            queue_depths=metrics.get("queue_depths", {}),
        )
        await self._manager.broadcast_to_room("global", global_event)

        # Broadcast individual queue updates
        queue_depths = metrics.get("queue_depths", {})
        for queue_name, depth in queue_depths.items():
            queue_event = QueueEvent(
                type=WebSocketEventType.QUEUE_DEPTH_CHANGED,
                queue_name=queue_name,
                depth=depth,
            )
            # Broadcast to both 'queues' room and specific queue room
            await self._manager.broadcast_to_rooms(
                [f"queue:{queue_name}", "queues"],
                queue_event,
            )

    def get_last_metrics(self) -> dict[str, Any]:
        """Get the most recently collected metrics.

        Returns:
            Dictionary of last collected metrics, or empty dict if none.
        """
        return self._last_metrics.copy()
