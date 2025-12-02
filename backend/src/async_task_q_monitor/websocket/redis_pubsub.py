"""Redis Pub/Sub adapter for horizontal scaling of WebSocket connections.

This module provides a Redis-based message broker that allows multiple
server instances to broadcast WebSocket events to each other. This enables
horizontal scaling where WebSocket clients can connect to any server instance
and still receive all relevant events.

Architecture:
    Server A ──┐
               ├──► Redis Pub/Sub ──► All Servers ──► Local WebSocket Clients
    Server B ──┘

Following best practices:
- Async Redis operations with redis.asyncio
- Graceful connection handling
- JSON serialization for messages
- Proper cleanup on shutdown
"""

import asyncio
import contextlib
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis.asyncio import Redis  # type: ignore[import-not-found]
    from redis.asyncio.client import PubSub  # type: ignore[import-not-found]

    from async_task_q_monitor.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class RedisPubSubBroker:
    """Redis Pub/Sub broker for distributed WebSocket event broadcasting.

    This broker enables horizontal scaling by:
    1. Publishing all local events to Redis channels
    2. Subscribing to Redis channels and broadcasting to local WebSocket clients

    Channel Structure:
        - `ws:events` - Main channel for all events
        - `ws:room:{room_name}` - Room-specific channels for targeted updates

    Example:
        >>> broker = RedisPubSubBroker(redis_url="redis://localhost:6379")
        >>> await broker.start()
        >>> await broker.publish("global", {"type": "metrics_updated", ...})
        >>> await broker.stop()
    """

    CHANNEL_PREFIX = "ws:room:"
    GLOBAL_CHANNEL = "ws:events"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        connection_manager: ConnectionManager | None = None,
    ) -> None:
        """Initialize the Redis Pub/Sub broker.

        Args:
            redis_url: Redis connection URL
            connection_manager: WebSocket connection manager for local broadcasts
        """
        self._redis_url = redis_url
        self._manager = connection_manager
        self._redis: Redis | None = None
        self._pubsub: PubSub | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._subscribed_rooms: set[str] = set()

    @property
    def is_running(self) -> bool:
        """Check if the broker is currently running."""
        return self._listener_task is not None and not self._listener_task.done()

    async def start(self) -> None:
        """Start the Redis Pub/Sub broker.

        Connects to Redis and starts listening for messages.
        """
        if self.is_running:
            logger.warning("RedisPubSubBroker already running")
            return

        try:
            # Import redis here to make it optional
            from redis.asyncio import from_url  # type: ignore[import-not-found]

            redis_client = from_url(self._redis_url, decode_responses=True)
            self._redis = redis_client
            pubsub = redis_client.pubsub()
            self._pubsub = pubsub

            # Subscribe to global channel
            await pubsub.subscribe(self.GLOBAL_CHANNEL)
            self._stop_event.clear()

            # Start listener task
            loop = asyncio.get_running_loop()
            self._listener_task = loop.create_task(
                self._listen(),
                name="redis_pubsub_listener",
            )

            logger.info("RedisPubSubBroker started, connected to %s", self._redis_url)

        except ImportError:
            logger.warning("redis package not installed, running without Redis Pub/Sub")
            return

        except Exception:
            logger.exception("Failed to start RedisPubSubBroker")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the Redis Pub/Sub broker and clean up connections."""
        if not self.is_running and self._redis is None:
            return

        logger.info("Stopping RedisPubSubBroker...")
        self._stop_event.set()

        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None

        # Unsubscribe and close pubsub
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
            except Exception:
                logger.debug("Error closing pubsub", exc_info=True)
            self._pubsub = None

        # Close Redis connection
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                logger.debug("Error closing Redis connection", exc_info=True)
            self._redis = None

        self._subscribed_rooms.clear()
        logger.info("RedisPubSubBroker stopped")

    async def subscribe_room(self, room: str) -> None:
        """Subscribe to a specific room's Redis channel.

        Args:
            room: Room name to subscribe to
        """
        if not self._pubsub or room in self._subscribed_rooms:
            return

        channel = f"{self.CHANNEL_PREFIX}{room}"
        await self._pubsub.subscribe(channel)
        self._subscribed_rooms.add(room)
        logger.debug("Subscribed to Redis channel: %s", channel)

    async def unsubscribe_room(self, room: str) -> None:
        """Unsubscribe from a specific room's Redis channel.

        Args:
            room: Room name to unsubscribe from
        """
        if not self._pubsub or room not in self._subscribed_rooms:
            return

        channel = f"{self.CHANNEL_PREFIX}{room}"
        await self._pubsub.unsubscribe(channel)
        self._subscribed_rooms.discard(room)
        logger.debug("Unsubscribed from Redis channel: %s", channel)

    async def publish(self, room: str, message: dict[str, Any]) -> int:
        """Publish a message to a room via Redis.

        Args:
            room: Room name to publish to
            message: Message dictionary to publish

        Returns:
            Number of subscribers that received the message
        """
        if not self._redis:
            logger.debug("Redis not connected, cannot publish")
            return 0

        try:
            channel = f"{self.CHANNEL_PREFIX}{room}"
            # Wrap message with room info for the listener
            wrapped = {"room": room, "message": message}
            result = await self._redis.publish(channel, json.dumps(wrapped))
            return int(result)
        except Exception:
            logger.exception("Error publishing to Redis")
            return 0

    async def publish_to_rooms(self, rooms: list[str], message: dict[str, Any]) -> int:
        """Publish a message to multiple rooms via Redis.

        Args:
            rooms: List of room names to publish to
            message: Message dictionary to publish

        Returns:
            Total number of subscribers that received the message
        """
        if not self._redis:
            return 0

        total = 0
        for room in rooms:
            total += await self.publish(room, message)
        return total

    async def _listen(self) -> None:
        """Listen for messages from Redis and broadcast to local WebSocket clients."""
        if not self._pubsub:
            return

        logger.debug("Starting Redis Pub/Sub listener")

        try:
            async for message in self._pubsub.listen():
                if self._stop_event.is_set():
                    break

                if message["type"] not in ("message", "pmessage"):
                    continue

                try:
                    await self._handle_message(message)
                except Exception:
                    logger.exception("Error handling Redis message")

        except asyncio.CancelledError:
            logger.debug("Redis listener cancelled")
            raise

        except Exception:
            logger.exception("Error in Redis listener")

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle a message received from Redis.

        Args:
            message: Redis message dictionary
        """
        if not self._manager:
            # Lazily import manager if not provided
            from async_task_q_monitor.websocket.manager import get_connection_manager

            self._manager = get_connection_manager()

        try:
            data = json.loads(message["data"])
            room = data.get("room", "global")
            payload = data.get("message", data)

            # Broadcast to local WebSocket clients
            await self._manager.broadcast_to_room(room, payload)

        except json.JSONDecodeError:
            logger.warning("Invalid JSON in Redis message: %s", message["data"])

        except Exception:
            logger.exception("Error processing Redis message")


# Global singleton instance
_broker: RedisPubSubBroker | None = None


def get_redis_broker() -> RedisPubSubBroker | None:
    """Get the global RedisPubSubBroker instance if configured.

    Returns:
        The global broker instance or None if not configured
    """
    return _broker


async def init_redis_broker(
    redis_url: str,
    connection_manager: ConnectionManager | None = None,
) -> RedisPubSubBroker:
    """Initialize and start the global Redis Pub/Sub broker.

    Args:
        redis_url: Redis connection URL
        connection_manager: WebSocket connection manager

    Returns:
        The initialized broker instance
    """
    global _broker

    if _broker is not None:
        await _broker.stop()

    _broker = RedisPubSubBroker(redis_url, connection_manager)
    await _broker.start()
    return _broker


async def shutdown_redis_broker() -> None:
    """Shutdown the global Redis Pub/Sub broker."""
    global _broker

    if _broker is not None:
        await _broker.stop()
        _broker = None
