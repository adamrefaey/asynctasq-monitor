"""Event consumer for Redis Pub/Sub events from workers.

This service subscribes to the Redis Pub/Sub channel where workers
publish task and worker events, and broadcasts them to connected WebSocket clients.

Architecture:
    Workers → Redis Pub/Sub → EventConsumer → EventBroadcaster → WebSocket Clients

Flow:
    1. Workers publish events to Redis Pub/Sub (via RedisEventEmitter)
    2. This consumer subscribes to the events channel
    3. Events are deserialized and routed to EventBroadcaster methods
    4. EventBroadcaster forwards events to connected WebSocket clients

Dependencies:
    - redis: For Redis Pub/Sub connection
    - msgpack: For event deserialization
"""

import asyncio
import logging
import os
from typing import Any

import msgpack
from redis.asyncio import Redis

from asynctasq_monitor.websocket.broadcaster import EventBroadcaster, get_event_broadcaster

logger = logging.getLogger(__name__)


class EventConsumer:
    """Consumes events from Redis Pub/Sub and broadcasts to WebSocket clients.

    Handles both TaskEvent and WorkerEvent types, routing them to the
    appropriate broadcaster methods for real-time UI updates.

    Configuration:
        - ATQ_REDIS_URL: Redis connection URL (default: redis://localhost:6379)
        - ATQ_EVENTS_CHANNEL: Pub/Sub channel name (default: asynctasq:events)

    Example:
        >>> consumer = EventConsumer()
        >>> await consumer.start()  # Starts listening for events
        >>> # ... application runs ...
        >>> await consumer.stop()   # Graceful shutdown
    """

    def __init__(
        self,
        redis_url: str | None = None,
        channel: str | None = None,
    ) -> None:
        """Initialize the event consumer.

        Args:
            redis_url: Redis connection URL (default from ATQ_REDIS_URL env var)
            channel: Pub/Sub channel name (default from ATQ_EVENTS_CHANNEL env var)
        """
        self.redis_url = redis_url or os.getenv("ATQ_REDIS_URL", "redis://localhost:6379")
        self.channel = channel or os.getenv("ATQ_EVENTS_CHANNEL", "asynctasq:events")
        self._client: Redis | None = None  # type: ignore[type-arg]
        self._pubsub: Any = None  # PubSub instance
        self._task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if the consumer is currently running."""
        return self._running and self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start consuming events from Redis Pub/Sub.

        Connects to Redis, subscribes to the events channel, and starts
        the background consumption loop.

        Raises:
            Exception: If connection to Redis fails
        """
        if self._running:
            logger.warning("EventConsumer already running")
            return

        try:
            self._client = Redis.from_url(self.redis_url, decode_responses=False)
            # Test connection
            await self._client.ping()  # type: ignore[misc]

            self._pubsub = self._client.pubsub()
            await self._pubsub.subscribe(self.channel)

            self._running = True
            self._task = asyncio.create_task(self._consume_loop(), name="event_consumer")
            logger.info("EventConsumer started, subscribed to %s", self.channel)

        except Exception as e:
            logger.error("Failed to start EventConsumer: %s", e)
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

        logger.info("EventConsumer stopped")

    async def _consume_loop(self) -> None:
        """Main consumption loop - reads and processes messages from Pub/Sub."""
        broadcaster = get_event_broadcaster()

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

                await self._handle_message(message["data"], broadcaster)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in event consumer loop")
                await asyncio.sleep(1.0)  # Backoff on error

    async def _handle_message(self, data: bytes, broadcaster: EventBroadcaster) -> None:
        """Handle a single message from Redis.

        Deserializes the event and routes it to the appropriate broadcaster method.

        Args:
            data: Raw msgpack-encoded event data
            broadcaster: EventBroadcaster to send events to
        """
        try:
            event = msgpack.unpackb(data, raw=False)
            event_type = event.get("event_type", "")

            # Route task events
            if event_type == "task_enqueued":
                await broadcaster.broadcast_task_enqueued(
                    task_id=event["task_id"],
                    task_name=event["task_name"],
                    queue=event["queue"],
                )
            elif event_type == "task_started":
                await broadcaster.broadcast_task_started(
                    task_id=event["task_id"],
                    task_name=event["task_name"],
                    queue=event["queue"],
                    worker_id=event["worker_id"],
                    attempt=event.get("attempt", 1),
                )
            elif event_type == "task_completed":
                await broadcaster.broadcast_task_completed(
                    task_id=event["task_id"],
                    task_name=event["task_name"],
                    queue=event["queue"],
                    worker_id=event.get("worker_id"),
                    duration_ms=event.get("duration_ms"),
                )
            elif event_type == "task_failed":
                await broadcaster.broadcast_task_failed(
                    task_id=event["task_id"],
                    task_name=event["task_name"],
                    queue=event["queue"],
                    worker_id=event.get("worker_id"),
                    error=event.get("error"),
                    attempt=event.get("attempt", 1),
                    duration_ms=event.get("duration_ms"),
                )
            elif event_type == "task_retrying":
                await broadcaster.broadcast_task_retrying(
                    task_id=event["task_id"],
                    task_name=event["task_name"],
                    queue=event["queue"],
                    attempt=event.get("attempt", 1),
                    error=event.get("error"),
                )

            # Route worker events
            elif event_type == "worker_online":
                await broadcaster.broadcast_worker_started(
                    worker_id=event["worker_id"],
                )
            elif event_type == "worker_heartbeat":
                # Calculate load percentage from active tasks
                # Assume 10 concurrency if not provided
                active = event.get("active", 0)
                load_percentage = min(active * 10.0, 100.0)  # Cap at 100%

                await broadcaster.broadcast_worker_heartbeat(
                    worker_id=event["worker_id"],
                    load_percentage=load_percentage,
                    tasks_processed=event.get("processed"),
                    uptime_seconds=event.get("uptime_seconds"),
                )
            elif event_type == "worker_offline":
                await broadcaster.broadcast_worker_stopped(
                    worker_id=event["worker_id"],
                    tasks_processed=event.get("processed"),
                    uptime_seconds=event.get("uptime_seconds"),
                )
            else:
                logger.warning("Unknown event type: %s", event_type)

        except Exception:
            logger.exception("Error handling event message")


# Global singleton
_consumer: EventConsumer | None = None


def get_event_consumer() -> EventConsumer:
    """Get or create the global EventConsumer singleton.

    Returns:
        The global EventConsumer instance
    """
    global _consumer
    if _consumer is None:
        _consumer = EventConsumer()
    return _consumer


def reset_event_consumer() -> None:
    """Reset the global EventConsumer singleton (for testing)."""
    global _consumer
    _consumer = None
