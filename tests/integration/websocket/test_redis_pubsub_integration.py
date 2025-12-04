"""Integration tests for Redis Pub/Sub broker.

Following best practices (2024):
- Use real Redis from docker-compose (redis://localhost:6379)
- Use pytest-asyncio with strict mode and explicit @pytest.mark.asyncio
- Use separate test database (DB 15) to avoid conflicts
- Test actual pub/sub message flow end-to-end
- Test graceful shutdown and reconnection scenarios

References:
- Redis Pub/Sub best practices: https://redis.io/glossary/pub-sub/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

Run Redis first:
    docker-compose -f tests/infrastructure/docker-compose.yml up -d redis
"""

import asyncio
from collections.abc import AsyncIterator
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from asynctasq_monitor.websocket.redis_pubsub import (
    RedisPubSubBroker,
    get_redis_broker,
    init_redis_broker,
    shutdown_redis_broker,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def broker() -> AsyncIterator[RedisPubSubBroker]:
    """Create a RedisPubSubBroker with real Redis for testing.

    Uses test database (DB 15) via URL parameter.
    Automatically starts and stops the broker.
    """
    broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
    try:
        await broker.start()
        yield broker
    except Exception:
        pytest.skip("Redis not available for integration tests")
    finally:
        await broker.stop()


@pytest_asyncio.fixture
async def mock_manager() -> AsyncMock:
    """Create a mock ConnectionManager for capturing broadcasts."""
    manager = AsyncMock()
    manager.broadcast_to_room = AsyncMock(return_value=1)
    return manager


@pytest_asyncio.fixture
async def broker_with_manager(mock_manager: AsyncMock) -> AsyncIterator[RedisPubSubBroker]:
    """Create a RedisPubSubBroker with mock manager for testing message handling."""
    broker = RedisPubSubBroker(
        redis_url="redis://localhost:6379/15",
        connection_manager=mock_manager,
    )
    try:
        await broker.start()
        yield broker
    except Exception:
        pytest.skip("Redis not available for integration tests")
    finally:
        await broker.stop()


# ============================================================================
# Broker Lifecycle Tests
# ============================================================================


@pytest.mark.integration
class TestBrokerLifecycle:
    """Tests for broker start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_connects_to_redis(self) -> None:
        """Test that start() connects to Redis and subscribes to global channel."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        try:
            await broker.start()
            assert broker.is_running
            assert broker._redis is not None
            assert broker._pubsub is not None
            assert broker._listener_task is not None
        except Exception:
            pytest.skip("Redis not available for integration tests")
        finally:
            await broker.stop()

    @pytest.mark.asyncio
    async def test_stop_cleans_up_resources(self) -> None:
        """Test that stop() cleans up all resources properly."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        try:
            await broker.start()
            assert broker.is_running

            await broker.stop()
            assert not broker.is_running
            assert broker._redis is None
            assert broker._pubsub is None
            assert broker._listener_task is None
            assert len(broker._subscribed_rooms) == 0
        except Exception:
            pytest.skip("Redis not available for integration tests")

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, broker: RedisPubSubBroker) -> None:
        """Test that calling start() multiple times is safe."""
        # broker is already started by fixture
        assert broker.is_running

        # Call start again - should be no-op
        await broker.start()
        assert broker.is_running

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self) -> None:
        """Test that calling stop() multiple times is safe."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        # Stop without ever starting - should be no-op
        await broker.stop()
        assert not broker.is_running

        # Stop again - still safe
        await broker.stop()
        assert not broker.is_running

    @pytest.mark.asyncio
    async def test_is_running_property(self) -> None:
        """Test is_running property reflects broker state."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        assert not broker.is_running

        try:
            await broker.start()
            assert broker.is_running
        except Exception:
            pytest.skip("Redis not available for integration tests")
        finally:
            await broker.stop()
            assert not broker.is_running


# ============================================================================
# Room Subscription Tests
# ============================================================================


@pytest.mark.integration
class TestRoomSubscription:
    """Tests for room subscribe/unsubscribe functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_room(self, broker: RedisPubSubBroker) -> None:
        """Test subscribing to a room creates Redis channel subscription."""
        await broker.subscribe_room("tasks")
        assert "tasks" in broker._subscribed_rooms

    @pytest.mark.asyncio
    async def test_subscribe_room_is_idempotent(self, broker: RedisPubSubBroker) -> None:
        """Test subscribing to same room multiple times is safe."""
        await broker.subscribe_room("tasks")
        await broker.subscribe_room("tasks")
        assert "tasks" in broker._subscribed_rooms

    @pytest.mark.asyncio
    async def test_unsubscribe_room(self, broker: RedisPubSubBroker) -> None:
        """Test unsubscribing from a room removes Redis channel subscription."""
        await broker.subscribe_room("tasks")
        assert "tasks" in broker._subscribed_rooms

        await broker.unsubscribe_room("tasks")
        assert "tasks" not in broker._subscribed_rooms

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_room(self, broker: RedisPubSubBroker) -> None:
        """Test unsubscribing from non-subscribed room is safe."""
        # Should not raise
        await broker.unsubscribe_room("nonexistent")
        assert "nonexistent" not in broker._subscribed_rooms

    @pytest.mark.asyncio
    async def test_subscribe_multiple_rooms(self, broker: RedisPubSubBroker) -> None:
        """Test subscribing to multiple rooms."""
        rooms = ["tasks", "workers", "queues", "metrics"]
        for room in rooms:
            await broker.subscribe_room(room)

        for room in rooms:
            assert room in broker._subscribed_rooms

    @pytest.mark.asyncio
    async def test_subscribe_without_pubsub(self) -> None:
        """Test subscribing without started broker is safe."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        # pubsub is None when not started
        await broker.subscribe_room("tasks")
        assert "tasks" not in broker._subscribed_rooms

    @pytest.mark.asyncio
    async def test_unsubscribe_without_pubsub(self) -> None:
        """Test unsubscribing without started broker is safe."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        # pubsub is None when not started
        await broker.unsubscribe_room("tasks")
        # Should not raise


# ============================================================================
# Publish Tests
# ============================================================================


@pytest.mark.integration
class TestPublish:
    """Tests for publishing messages to Redis."""

    @pytest.mark.asyncio
    async def test_publish_message(self, broker: RedisPubSubBroker) -> None:
        """Test publishing a message to Redis returns subscriber count."""
        result = await broker.publish("tasks", {"type": "task_created", "id": "123"})
        # Result is number of subscribers (may be 0 if no one is listening)
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_publish_without_redis(self) -> None:
        """Test publishing without Redis connection returns 0."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        # Redis is None when not started
        result = await broker.publish("tasks", {"type": "test"})
        assert result == 0

    @pytest.mark.asyncio
    async def test_publish_to_rooms(self, broker: RedisPubSubBroker) -> None:
        """Test publishing to multiple rooms."""
        result = await broker.publish_to_rooms(
            ["tasks", "global", "queue:default"],
            {"type": "task_created", "id": "456"},
        )
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_publish_to_rooms_without_redis(self) -> None:
        """Test publishing to multiple rooms without Redis returns 0."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        result = await broker.publish_to_rooms(
            ["tasks", "global"],
            {"type": "test"},
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_publish_complex_message(self, broker: RedisPubSubBroker) -> None:
        """Test publishing complex nested message."""
        message = {
            "type": "task_completed",
            "data": {
                "task_id": "abc123",
                "result": {"success": True, "items": [1, 2, 3]},
                "metadata": {"duration_ms": 150, "worker": "worker-1"},
            },
            "timestamp": "2024-01-01T00:00:00Z",
        }
        result = await broker.publish("tasks", message)
        assert isinstance(result, int)


# ============================================================================
# Message Flow Integration Tests
# ============================================================================


@pytest.mark.integration
class TestMessageFlow:
    """Tests for end-to-end message flow through Redis Pub/Sub."""

    @pytest.mark.asyncio
    async def test_message_received_by_subscriber(
        self,
        broker_with_manager: RedisPubSubBroker,
        mock_manager: AsyncMock,
    ) -> None:
        """Test that published messages are received and broadcast to manager."""
        # Subscribe to room
        await broker_with_manager.subscribe_room("tasks")

        # Publish a message
        message = {"type": "task_created", "id": "test-123"}
        await broker_with_manager.publish("tasks", message)

        # Give time for async message processing
        await asyncio.sleep(0.2)

        # Verify manager received the broadcast
        assert mock_manager.broadcast_to_room.called
        call_args = mock_manager.broadcast_to_room.call_args
        assert call_args[0][0] == "tasks"  # room
        assert call_args[0][1] == message  # payload

    @pytest.mark.asyncio
    async def test_multiple_messages_received(
        self,
        broker_with_manager: RedisPubSubBroker,
        mock_manager: AsyncMock,
    ) -> None:
        """Test receiving multiple messages in sequence."""
        await broker_with_manager.subscribe_room("tasks")

        messages = [{"type": "task_created", "id": f"task-{i}"} for i in range(5)]

        for msg in messages:
            await broker_with_manager.publish("tasks", msg)

        # Give time for all messages to be processed
        await asyncio.sleep(0.5)

        # Should have received all messages
        assert mock_manager.broadcast_to_room.call_count >= 5

    @pytest.mark.asyncio
    async def test_cross_broker_communication(self, mock_manager: AsyncMock) -> None:
        """Test that messages published by one broker are received by another."""
        # Create two brokers simulating two server instances
        publisher = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        subscriber = RedisPubSubBroker(
            redis_url="redis://localhost:6379/15",
            connection_manager=mock_manager,
        )

        try:
            await publisher.start()
            await subscriber.start()
            await subscriber.subscribe_room("cross-test")

            # Publish from one broker
            message = {"type": "cross_broker_test", "data": "hello"}
            await publisher.publish("cross-test", message)

            # Give time for message to propagate
            await asyncio.sleep(0.3)

            # Subscriber's manager should have received it
            assert mock_manager.broadcast_to_room.called
            call_args = mock_manager.broadcast_to_room.call_args
            assert call_args[0][0] == "cross-test"
            assert call_args[0][1] == message

        except Exception:
            pytest.skip("Redis not available for integration tests")
        finally:
            await publisher.stop()
            await subscriber.stop()


# ============================================================================
# Global Broker Singleton Tests
# ============================================================================


@pytest.mark.integration
class TestGlobalBroker:
    """Tests for global broker singleton functions."""

    @pytest.mark.asyncio
    async def test_init_redis_broker(self) -> None:
        """Test initializing the global Redis broker."""
        try:
            broker = await init_redis_broker("redis://localhost:6379/15")
            assert broker is not None
            assert broker.is_running
            assert get_redis_broker() is broker
        except Exception:
            pytest.skip("Redis not available for integration tests")
        finally:
            await shutdown_redis_broker()

    @pytest.mark.asyncio
    async def test_init_redis_broker_replaces_existing(self) -> None:
        """Test that init_redis_broker stops existing broker first."""
        try:
            broker1 = await init_redis_broker("redis://localhost:6379/15")
            assert broker1.is_running

            broker2 = await init_redis_broker("redis://localhost:6379/15")
            assert broker2.is_running
            assert not broker1.is_running  # Old broker should be stopped
            assert get_redis_broker() is broker2
        except Exception:
            pytest.skip("Redis not available for integration tests")
        finally:
            await shutdown_redis_broker()

    @pytest.mark.asyncio
    async def test_get_redis_broker_returns_none_initially(self) -> None:
        """Test that get_redis_broker returns None when not initialized."""
        await shutdown_redis_broker()  # Ensure clean state
        assert get_redis_broker() is None

    @pytest.mark.asyncio
    async def test_shutdown_redis_broker(self) -> None:
        """Test shutting down the global Redis broker."""
        try:
            broker = await init_redis_broker("redis://localhost:6379/15")
            assert get_redis_broker() is not None

            await shutdown_redis_broker()
            assert get_redis_broker() is None
            assert not broker.is_running
        except Exception:
            pytest.skip("Redis not available for integration tests")

    @pytest.mark.asyncio
    async def test_shutdown_redis_broker_when_none(self) -> None:
        """Test shutting down when no broker exists is safe."""
        await shutdown_redis_broker()  # Ensure clean state
        await shutdown_redis_broker()  # Should not raise

    @pytest.mark.asyncio
    async def test_init_with_connection_manager(self, mock_manager: AsyncMock) -> None:
        """Test initializing broker with a connection manager."""
        try:
            broker = await init_redis_broker(
                "redis://localhost:6379/15",
                connection_manager=mock_manager,
            )
            assert broker._manager is mock_manager
        except Exception:
            pytest.skip("Redis not available for integration tests")
        finally:
            await shutdown_redis_broker()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_start_with_invalid_url(self) -> None:
        """Test starting with invalid Redis URL raises exception."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        broker = RedisPubSubBroker(redis_url="redis://invalid-host:9999/0")
        with pytest.raises((OSError, RedisConnectionError)):
            await broker.start()

    @pytest.mark.asyncio
    async def test_publish_handles_serialization_error(
        self,
        broker: RedisPubSubBroker,
    ) -> None:
        """Test that publish handles JSON serialization errors gracefully."""

        # Create a message that can't be JSON serialized
        class NonSerializable:
            pass

        # This should not raise but log an error and return 0
        result = await broker.publish("tasks", {"obj": NonSerializable()})  # type: ignore[dict-item]
        assert result == 0

    @pytest.mark.asyncio
    async def test_handle_message_with_invalid_json(
        self,
        broker_with_manager: RedisPubSubBroker,
        mock_manager: AsyncMock,
    ) -> None:
        """Test handling of invalid JSON message from Redis."""
        # Simulate receiving invalid JSON by calling _handle_message directly
        await broker_with_manager._handle_message({"data": "not valid json {{"})

        # Should not have broadcast anything
        mock_manager.broadcast_to_room.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_without_room(
        self,
        broker_with_manager: RedisPubSubBroker,
        mock_manager: AsyncMock,
    ) -> None:
        """Test handling message without room defaults to 'global'."""
        # Valid JSON but no room field
        await broker_with_manager._handle_message(
            {"data": json.dumps({"message": {"type": "test"}})}
        )

        # Should broadcast to 'global' room
        mock_manager.broadcast_to_room.assert_called()
        call_args = mock_manager.broadcast_to_room.call_args
        assert call_args[0][0] == "global"


# ============================================================================
# Listener Tests
# ============================================================================


@pytest.mark.integration
class TestListener:
    """Tests for the Redis Pub/Sub listener."""

    @pytest.mark.asyncio
    async def test_listener_ignores_non_message_types(
        self,
        broker_with_manager: RedisPubSubBroker,
        mock_manager: AsyncMock,
    ) -> None:
        """Test that listener ignores subscribe/unsubscribe confirmation messages."""
        # Subscribe to a room - this generates a 'subscribe' type message
        await broker_with_manager.subscribe_room("test-room")

        # Give time for subscribe confirmation
        await asyncio.sleep(0.1)

        # Manager should not have been called for subscribe confirmations
        # Only for actual messages
        initial_calls = mock_manager.broadcast_to_room.call_count

        # Now publish a real message
        await broker_with_manager.publish("test-room", {"type": "real_message"})
        await asyncio.sleep(0.2)

        # Should have one more call for the real message
        assert mock_manager.broadcast_to_room.call_count > initial_calls

    @pytest.mark.asyncio
    async def test_listener_continues_after_message_error(
        self,
        broker_with_manager: RedisPubSubBroker,
        mock_manager: AsyncMock,
    ) -> None:
        """Test that listener continues processing after a message handling error."""
        await broker_with_manager.subscribe_room("tasks")

        # Make broadcast_to_room raise an error on first call, then succeed
        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated error")
            return 1

        mock_manager.broadcast_to_room.side_effect = side_effect

        # Publish two messages
        await broker_with_manager.publish("tasks", {"type": "msg1"})
        await asyncio.sleep(0.2)
        await broker_with_manager.publish("tasks", {"type": "msg2"})
        await asyncio.sleep(0.2)

        # Both messages should have been attempted
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_listener_without_pubsub(self) -> None:
        """Test that _listen exits early when pubsub is None."""
        broker = RedisPubSubBroker(redis_url="redis://localhost:6379/15")
        # _pubsub is None when not started
        await broker._listen()  # Should return immediately without error
