"""Event handler for TUI real-time updates.

This module provides the TUIEventHandler class that bridges Redis Pub/Sub
events to Textual UI updates using proper async patterns.

Best Practices (2024-2025):
- Uses @work decorator for background task management
- Uses call_from_thread for thread-safe UI updates
- Properly handles worker cancellation
- Implements graceful shutdown with cleanup
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
import logging
from typing import TYPE_CHECKING, Any

import msgpack
from redis.asyncio import Redis
from textual.message import Message

if TYPE_CHECKING:
    from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

logger = logging.getLogger(__name__)


class TUIEventType(str, Enum):
    """Event types that the TUI cares about."""

    # Task events
    TASK_ENQUEUED = "task_enqueued"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_RETRYING = "task_retrying"

    # Worker events
    WORKER_ONLINE = "worker_online"
    WORKER_HEARTBEAT = "worker_heartbeat"
    WORKER_OFFLINE = "worker_offline"


@dataclass
class TUIEvent:
    """A parsed event from Redis for TUI consumption.

    Attributes:
        type: The type of event.
        data: The raw event data dictionary.
    """

    type: TUIEventType
    data: dict[str, Any]

    @property
    def task_id(self) -> str | None:
        """Get task ID if this is a task event."""
        return self.data.get("task_id")

    @property
    def task_name(self) -> str | None:
        """Get task name if available."""
        return self.data.get("task_name")

    @property
    def queue(self) -> str | None:
        """Get queue name if available."""
        return self.data.get("queue")

    @property
    def worker_id(self) -> str | None:
        """Get worker ID if available."""
        return self.data.get("worker_id")


class EventReceived(Message):
    """Message posted when a new event is received from Redis.

    This message is posted to the app's message queue for thread-safe
    handling of UI updates.
    """

    def __init__(self, event: TUIEvent) -> None:
        """Initialize the message.

        Args:
            event: The parsed TUI event.
        """
        super().__init__()
        self.event = event


class ConnectionStatusChanged(Message):
    """Message posted when Redis connection status changes.

    Attributes:
        connected: Whether we're connected to Redis.
        error: Error message if disconnected due to error.
    """

    def __init__(self, connected: bool, error: str | None = None) -> None:
        """Initialize the message.

        Args:
            connected: Whether connected to Redis.
            error: Error message if applicable.
        """
        super().__init__()
        self.connected = connected
        self.error = error


class TUIEventConsumer:
    """Consumes events from Redis Pub/Sub for TUI real-time updates.

    This consumer is designed specifically for the TUI and uses Textual's
    message system for thread-safe UI updates. It differs from the
    WebSocket-based EventConsumer by posting messages directly to the app.

    Example:
        >>> consumer = TUIEventConsumer(app, redis_url="redis://localhost:6379")
        >>> await consumer.start()  # Starts listening in background
        >>> # Events are now posted to the app
        >>> await consumer.stop()   # Graceful shutdown
    """

    def __init__(
        self,
        app: "AsyncTasQMonitorTUI",
        redis_url: str = "redis://localhost:6379",
        channel: str = "asynctasq:events",
    ) -> None:
        """Initialize the TUI event consumer.

        Args:
            app: The Textual app to post events to.
            redis_url: Redis connection URL.
            channel: Pub/Sub channel name.
        """
        self.app = app
        self.redis_url = redis_url
        self.channel = channel
        self._client: Redis | None = None  # type: ignore[type-arg]
        self._pubsub: Any = None
        self._running = False
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        """Check if the consumer is currently running."""
        return self._running and self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start consuming events from Redis.

        Connects to Redis, subscribes to the events channel, and starts
        the background consumption loop. Posts ConnectionStatusChanged
        messages to indicate connection state.
        """
        if self._running:
            logger.warning("TUIEventConsumer already running")
            return

        try:
            self._client = Redis.from_url(self.redis_url, decode_responses=False)
            await self._client.ping()  # type: ignore[misc]

            self._pubsub = self._client.pubsub()
            await self._pubsub.subscribe(self.channel)

            self._running = True
            self._task = asyncio.create_task(self._consume_loop(), name="tui_event_consumer")

            self.app.post_message(ConnectionStatusChanged(connected=True))
            logger.info("TUIEventConsumer started, subscribed to %s", self.channel)

        except Exception as e:
            logger.error("Failed to start TUIEventConsumer: %s", e)
            self.app.post_message(ConnectionStatusChanged(connected=False, error=str(e)))
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop consuming events and cleanup resources."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(self.channel)
                await self._pubsub.aclose()
            except Exception as e:
                logger.debug("Error closing pubsub: %s", e)
            self._pubsub = None

        if self._client:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.debug("Error closing redis client: %s", e)
            self._client = None

        logger.info("TUIEventConsumer stopped")

    async def _consume_loop(self) -> None:
        """Main consumption loop - reads and processes messages from Pub/Sub."""
        while self._running and self._pubsub:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message is None:
                    continue

                if message["type"] != "message":
                    continue

                await self._handle_message(message["data"])

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in TUI event consumer loop")
                await asyncio.sleep(1.0)  # Backoff on error

    async def _handle_message(self, data: bytes) -> None:
        """Handle a single message from Redis.

        Parses the event and posts it to the app's message queue.

        Args:
            data: Raw msgpack-encoded event data.
        """
        try:
            raw_event = msgpack.unpackb(data, raw=False)
            event_type_str = raw_event.get("event_type", "")

            try:
                event_type = TUIEventType(event_type_str)
            except ValueError:
                logger.debug("Unknown event type: %s", event_type_str)
                return

            event = TUIEvent(type=event_type, data=raw_event)
            self.app.post_message(EventReceived(event))

        except Exception:
            logger.exception("Error handling event message")


class MetricsTracker:
    """Tracks task metrics for the dashboard.

    Provides in-memory counts of task states that can be updated
    in real-time from events and periodically synced with Redis.
    """

    def __init__(self) -> None:
        """Initialize the metrics tracker."""
        self.pending = 0
        self.running = 0
        self.completed = 0
        self.failed = 0
        self._throughput_history: list[float] = []
        self._last_completed_count = 0
        self._last_sample_time: float | None = None

    def handle_event(self, event: TUIEvent) -> None:
        """Update metrics based on an event.

        Args:
            event: The event to process.
        """
        match event.type:
            case TUIEventType.TASK_ENQUEUED:
                self.pending += 1
            case TUIEventType.TASK_STARTED:
                self.pending = max(0, self.pending - 1)
                self.running += 1
            case TUIEventType.TASK_COMPLETED:
                self.running = max(0, self.running - 1)
                self.completed += 1
            case TUIEventType.TASK_FAILED:
                self.running = max(0, self.running - 1)
                self.failed += 1
            case TUIEventType.TASK_RETRYING:
                self.running = max(0, self.running - 1)
                self.pending += 1

    def set_metrics(self, pending: int, running: int, completed: int, failed: int) -> None:
        """Set metrics from an external source (e.g., API refresh).

        Args:
            pending: Number of pending tasks.
            running: Number of running tasks.
            completed: Number of completed tasks.
            failed: Number of failed tasks.
        """
        self.pending = pending
        self.running = running
        self.completed = completed
        self.failed = failed

    def sample_throughput(self, current_time: float) -> float | None:
        """Sample current throughput rate.

        Calculates tasks/minute based on completed count change
        since last sample.

        Args:
            current_time: Current timestamp in seconds.

        Returns:
            Tasks per minute, or None if this is the first sample.
        """
        if self._last_sample_time is None:
            self._last_sample_time = current_time
            self._last_completed_count = self.completed
            return None

        elapsed = current_time - self._last_sample_time
        if elapsed < 1.0:  # Minimum 1 second between samples
            return None

        completed_delta = self.completed - self._last_completed_count
        tasks_per_minute = (completed_delta / elapsed) * 60.0

        self._last_sample_time = current_time
        self._last_completed_count = self.completed

        # Keep last 60 samples
        self._throughput_history.append(tasks_per_minute)
        if len(self._throughput_history) > 60:
            self._throughput_history = self._throughput_history[-60:]

        return tasks_per_minute

    @property
    def throughput_history(self) -> list[float]:
        """Get the throughput history for sparkline display."""
        return self._throughput_history.copy()
