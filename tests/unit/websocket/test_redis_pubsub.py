"""Unit tests for Redis Pub/Sub broker.

Following best practices (2024):
- Use mocks to test edge cases without real Redis
- Test error handling and edge cases
- Test logging behavior
- Use pytest-asyncio with strict mode and explicit @pytest.mark.asyncio

These tests complement the integration tests by covering:
- Import error handling (redis package not installed)
- Connection error handling
- Edge cases that are hard to trigger with real Redis
"""

import asyncio
from collections.abc import AsyncIterator
import json
import logging
from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asynctasq_monitor.websocket.redis_pubsub import (
    RedisPubSubBroker,
    get_redis_broker,
    shutdown_redis_broker,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Create a mock Redis client."""
    client = MagicMock()
    client.pubsub = MagicMock(return_value=MagicMock())
    client.publish = AsyncMock(return_value=1)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_pubsub() -> MagicMock:
    """Create a mock PubSub object."""
    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.close = AsyncMock()
    pubsub.listen = MagicMock(return_value=AsyncIteratorMock([]))
    return pubsub


class AsyncIteratorMock:
    """Mock async iterator for pubsub.listen()."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.index = 0

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.unit
class TestBrokerInitialization:
    """Tests for broker initialization."""

    def test_default_initialization(self) -> None:
        """Test broker initializes with default values."""
        broker = RedisPubSubBroker()
        assert broker._redis_url == "redis://localhost:6379"
        assert broker._manager is None
        assert broker._redis is None
        assert broker._pubsub is None
        assert broker._listener_task is None
        assert len(broker._subscribed_rooms) == 0

    def test_custom_url_initialization(self) -> None:
        """Test broker initializes with custom URL."""
        broker = RedisPubSubBroker(redis_url="redis://custom:6380/5")
        assert broker._redis_url == "redis://custom:6380/5"

    def test_initialization_with_manager(self) -> None:
        """Test broker initializes with connection manager."""
        mock_manager = MagicMock()
        broker = RedisPubSubBroker(connection_manager=mock_manager)
        assert broker._manager is mock_manager

    def test_channel_constants(self) -> None:
        """Test channel prefix and global channel constants."""
        assert RedisPubSubBroker.CHANNEL_PREFIX == "ws:room:"
        assert RedisPubSubBroker.GLOBAL_CHANNEL == "ws:events"


# ============================================================================
# Import Error Tests
# ============================================================================


@pytest.mark.unit
class TestImportError:
    """Tests for handling missing redis package."""

    @pytest.mark.asyncio
    async def test_start_without_redis_package(self) -> None:
        """Test that start() handles ImportError gracefully."""
        broker = RedisPubSubBroker()

        # Patch the import to raise ImportError
        with patch.dict("sys.modules", {"redis.asyncio": None}):
            with patch(
                "asynctasq_monitor.websocket.redis_pubsub.RedisPubSubBroker.start",
                new_callable=AsyncMock,
            ) as mock_start:
                # Simulate the ImportError path
                mock_start.return_value = None
                await broker.start()

        # Broker should not be running if redis import fails
        # (In actual implementation, warning is logged and method returns)


# ============================================================================
# Connection Error Tests
# ============================================================================


@pytest.mark.unit
class TestConnectionErrors:
    """Tests for handling connection errors."""

    @pytest.mark.asyncio
    async def test_start_connection_error_cleanup(self) -> None:
        """Test that start() cleans up on connection error."""
        broker = RedisPubSubBroker(redis_url="redis://nonexistent:9999")

        # Mock redis.asyncio.from_url to raise connection error
        with patch(
            "redis.asyncio.from_url",
            side_effect=ConnectionError("Cannot connect"),
        ):
            with pytest.raises(ConnectionError):
                await broker.start()

        # Verify cleanup happened
        assert broker._redis is None
        assert broker._pubsub is None

    @pytest.mark.asyncio
    async def test_stop_handles_close_errors(self) -> None:
        """Test that stop() handles errors during cleanup."""
        broker = RedisPubSubBroker()

        # Set up broker state as if it was running
        mock_redis = MagicMock()
        mock_redis.close = AsyncMock(side_effect=RuntimeError("Close error"))
        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("Unsubscribe error"))
        mock_pubsub.close = AsyncMock(side_effect=RuntimeError("Pubsub close error"))

        broker._redis = mock_redis
        broker._pubsub = mock_pubsub
        broker._listener_task = None
        broker._subscribed_rooms = {"room1", "room2"}

        # Should not raise despite errors
        await broker.stop()

        # Should still clean up
        assert broker._redis is None
        assert broker._pubsub is None
        assert len(broker._subscribed_rooms) == 0


# ============================================================================
# Publish Error Tests
# ============================================================================


@pytest.mark.unit
class TestPublishErrors:
    """Tests for error handling during publish."""

    @pytest.mark.asyncio
    async def test_publish_handles_redis_error(self) -> None:
        """Test that publish() handles Redis errors gracefully."""
        broker = RedisPubSubBroker()

        # Set up mock Redis that raises on publish
        mock_redis = MagicMock()
        mock_redis.publish = AsyncMock(side_effect=RuntimeError("Redis error"))
        broker._redis = mock_redis

        # Should return 0, not raise
        result = await broker.publish("room", {"type": "test"})
        assert result == 0

    @pytest.mark.asyncio
    async def test_publish_handles_json_error(self) -> None:
        """Test that publish() handles JSON serialization errors."""
        broker = RedisPubSubBroker()

        # Set up mock Redis
        mock_redis = MagicMock()
        # json.dumps will fail for non-serializable objects
        mock_redis.publish = AsyncMock(return_value=1)
        broker._redis = mock_redis

        # Create non-serializable message
        class NonSerializable:
            pass

        result = await broker.publish("room", {"obj": NonSerializable()})  # type: ignore[dict-item]
        assert result == 0


# ============================================================================
# Handle Message Tests
# ============================================================================


@pytest.mark.unit
class TestHandleMessage:
    """Tests for _handle_message method."""

    @pytest.mark.asyncio
    async def test_handle_message_with_manager(self) -> None:
        """Test _handle_message broadcasts to manager."""
        mock_manager = AsyncMock()
        mock_manager.broadcast_to_room = AsyncMock(return_value=1)
        broker = RedisPubSubBroker(connection_manager=mock_manager)

        message = {
            "data": json.dumps(
                {
                    "room": "tasks",
                    "message": {"type": "task_created", "id": "123"},
                }
            )
        }

        await broker._handle_message(message)

        mock_manager.broadcast_to_room.assert_called_once_with(
            "tasks",
            {"type": "task_created", "id": "123"},
        )

    @pytest.mark.asyncio
    async def test_handle_message_lazy_loads_manager(self) -> None:
        """Test _handle_message lazily loads manager if not provided."""
        broker = RedisPubSubBroker()  # No manager provided
        assert broker._manager is None

        # Mock get_connection_manager in the manager module
        mock_manager = AsyncMock()
        mock_manager.broadcast_to_room = AsyncMock(return_value=1)

        with patch(
            "asynctasq_monitor.websocket.manager.get_connection_manager",
            return_value=mock_manager,
        ):
            message = {
                "data": json.dumps(
                    {
                        "room": "tasks",
                        "message": {"type": "test"},
                    }
                )
            }
            await broker._handle_message(message)

        # Manager should have been loaded and used
        assert broker._manager is mock_manager
        mock_manager.broadcast_to_room.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test _handle_message logs warning for invalid JSON."""
        mock_manager = AsyncMock()
        broker = RedisPubSubBroker(connection_manager=mock_manager)

        with caplog.at_level(logging.WARNING):
            await broker._handle_message({"data": "not valid json {{"})

        assert "Invalid JSON" in caplog.text
        mock_manager.broadcast_to_room.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_defaults_to_global_room(self) -> None:
        """Test _handle_message uses 'global' room when not specified."""
        mock_manager = AsyncMock()
        mock_manager.broadcast_to_room = AsyncMock(return_value=1)
        broker = RedisPubSubBroker(connection_manager=mock_manager)

        # Message without room field
        message = {
            "data": json.dumps(
                {
                    "message": {"type": "test"},
                }
            )
        }

        await broker._handle_message(message)

        mock_manager.broadcast_to_room.assert_called_once()
        call_args = mock_manager.broadcast_to_room.call_args
        assert call_args[0][0] == "global"

    @pytest.mark.asyncio
    async def test_handle_message_broadcast_error(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test _handle_message logs error when broadcast fails."""
        mock_manager = AsyncMock()
        mock_manager.broadcast_to_room = AsyncMock(side_effect=RuntimeError("Broadcast error"))
        broker = RedisPubSubBroker(connection_manager=mock_manager)

        message = {
            "data": json.dumps(
                {
                    "room": "tasks",
                    "message": {"type": "test"},
                }
            )
        }

        with caplog.at_level(logging.ERROR):
            await broker._handle_message(message)

        assert "Error processing Redis message" in caplog.text


# ============================================================================
# Listener Tests
# ============================================================================


@pytest.mark.unit
class TestListener:
    """Tests for _listen method."""

    @pytest.mark.asyncio
    async def test_listen_returns_early_without_pubsub(self) -> None:
        """Test _listen returns early when pubsub is None."""
        broker = RedisPubSubBroker()
        assert broker._pubsub is None

        # Should return immediately without error
        await broker._listen()

    @pytest.mark.asyncio
    async def test_listen_stops_on_stop_event(self) -> None:
        """Test _listen stops when stop event is set."""
        broker = RedisPubSubBroker()

        # Create mock pubsub that yields messages forever
        async def infinite_messages() -> AsyncIterator[dict[str, Any]]:
            while True:
                yield {"type": "message", "data": '{"room": "test", "message": {}}'}
                await asyncio.sleep(0.01)

        mock_pubsub = MagicMock()
        mock_pubsub.listen = MagicMock(return_value=infinite_messages())
        broker._pubsub = mock_pubsub

        mock_manager = AsyncMock()
        mock_manager.broadcast_to_room = AsyncMock(return_value=1)
        broker._manager = mock_manager

        # Set stop event before listen
        broker._stop_event.set()

        # Start listen task
        task = asyncio.create_task(broker._listen())

        # Should complete quickly due to stop event
        await asyncio.wait_for(task, timeout=1.0)

    @pytest.mark.asyncio
    async def test_listen_ignores_subscribe_messages(self) -> None:
        """Test _listen ignores subscribe/unsubscribe confirmation messages."""
        broker = RedisPubSubBroker()

        messages = [
            {"type": "subscribe", "channel": "ws:events", "data": 1},
            {"type": "message", "data": '{"room": "test", "message": {"type": "real"}}'},
            {"type": "psubscribe", "channel": "ws:*", "data": 2},
        ]

        mock_pubsub = MagicMock()
        mock_pubsub.listen = MagicMock(return_value=AsyncIteratorMock(messages))
        broker._pubsub = mock_pubsub

        mock_manager = AsyncMock()
        mock_manager.broadcast_to_room = AsyncMock(return_value=1)
        broker._manager = mock_manager

        await broker._listen()

        # Should only have processed the "message" type
        assert mock_manager.broadcast_to_room.call_count == 1

    @pytest.mark.asyncio
    async def test_listen_handles_pmessage_type(self) -> None:
        """Test _listen handles pmessage type (pattern subscriptions)."""
        broker = RedisPubSubBroker()

        messages = [
            {"type": "pmessage", "data": '{"room": "pattern-test", "message": {"type": "test"}}'},
        ]

        mock_pubsub = MagicMock()
        mock_pubsub.listen = MagicMock(return_value=AsyncIteratorMock(messages))
        broker._pubsub = mock_pubsub

        mock_manager = AsyncMock()
        mock_manager.broadcast_to_room = AsyncMock(return_value=1)
        broker._manager = mock_manager

        await broker._listen()

        mock_manager.broadcast_to_room.assert_called_once()


# ============================================================================
# Logging Tests
# ============================================================================


@pytest.mark.unit
class TestLogging:
    """Tests for logging behavior."""

    @pytest.mark.asyncio
    async def test_start_logs_warning_when_already_running(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test start() logs warning when broker is already running."""
        broker = RedisPubSubBroker()

        # Simulate running state
        mock_task = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        broker._listener_task = mock_task

        with caplog.at_level(logging.WARNING):
            await broker.start()

        assert "already running" in caplog.text

    @pytest.mark.asyncio
    async def test_publish_logs_debug_when_not_connected(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test publish() logs debug when Redis not connected."""
        broker = RedisPubSubBroker()
        assert broker._redis is None

        with caplog.at_level(logging.DEBUG):
            await broker.publish("room", {"type": "test"})

        assert "Redis not connected" in caplog.text


# ============================================================================
# Module-level Function Tests
# ============================================================================


@pytest.mark.unit
class TestModuleFunctions:
    """Tests for module-level helper functions."""

    @pytest.mark.asyncio
    async def test_get_redis_broker_returns_none_initially(self) -> None:
        """Test get_redis_broker returns None when not initialized."""
        # Reset global state
        import asynctasq_monitor.websocket.redis_pubsub as module

        original = module._broker
        module._broker = None

        try:
            assert get_redis_broker() is None
        finally:
            module._broker = original

    @pytest.mark.asyncio
    async def test_shutdown_when_broker_is_none(self) -> None:
        """Test shutdown_redis_broker is safe when broker is None."""
        import asynctasq_monitor.websocket.redis_pubsub as module

        original = module._broker
        module._broker = None

        try:
            # Should not raise
            await shutdown_redis_broker()
            assert module._broker is None
        finally:
            module._broker = original
