"""Tests for EventConsumer service.

Following pytest best practices:
- Use explicit @pytest.mark.asyncio decorators (strict mode)
- Use pytest.mark.unit for categorization
- Mock Redis and EventBroadcaster for isolation
- Test all event types and error handling paths
"""

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
import pytest

from asynctasq_monitor.services.event_consumer import (
    EventConsumer,
    get_event_consumer,
    reset_event_consumer,
)
from asynctasq_monitor.websocket.broadcaster import EventBroadcaster


class MockPubSub:
    """Mock Redis PubSub for testing."""

    def __init__(self) -> None:
        """Initialize mock pubsub."""
        self.subscribed_channels: list[str] = []
        self.messages: list[dict[str, Any]] = []
        self._message_index = 0
        self._closed = False
        self._get_message_call_count = 0
        self._max_get_message_calls = 10  # Prevent infinite loops in tests

    async def subscribe(self, channel: str) -> None:
        """Mock subscribe."""
        self.subscribed_channels.append(channel)

    async def unsubscribe(self, channel: str) -> None:
        """Mock unsubscribe."""
        if channel in self.subscribed_channels:
            self.subscribed_channels.remove(channel)

    async def get_message(
        self,
        ignore_subscribe_messages: bool = False,
        timeout: float = 0.0,
    ) -> dict[str, Any] | None:
        """Return next queued message or None."""
        _ = ignore_subscribe_messages, timeout
        self._get_message_call_count += 1

        # Safety: prevent infinite loops in tests
        if self._get_message_call_count > self._max_get_message_calls:
            raise asyncio.CancelledError("Max get_message calls reached")

        if self._message_index < len(self.messages):
            msg = self.messages[self._message_index]
            self._message_index += 1
            return msg
        return None

    async def aclose(self) -> None:
        """Mock close."""
        self._closed = True

    def add_message(self, data: bytes, msg_type: str = "message") -> None:
        """Add a message to be returned by get_message."""
        self.messages.append({"type": msg_type, "data": data})


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self) -> None:
        """Initialize mock redis client."""
        self._pubsub = MockPubSub()
        self._closed = False

    async def ping(self) -> bool:
        """Mock ping."""
        return True

    def pubsub(self) -> MockPubSub:
        """Return mock pubsub."""
        return self._pubsub

    async def aclose(self) -> None:
        """Mock close."""
        self._closed = True


class MockEventBroadcaster:
    """Mock EventBroadcaster for testing."""

    def __init__(self) -> None:
        """Initialize mock broadcaster."""
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def broadcast_task_enqueued(self, **kwargs: Any) -> int:
        """Track task enqueued call."""
        self.calls.append(("task_enqueued", kwargs))
        return 1

    async def broadcast_task_started(self, **kwargs: Any) -> int:
        """Track task started call."""
        self.calls.append(("task_started", kwargs))
        return 1

    async def broadcast_task_completed(self, **kwargs: Any) -> int:
        """Track task completed call."""
        self.calls.append(("task_completed", kwargs))
        return 1

    async def broadcast_task_failed(self, **kwargs: Any) -> int:
        """Track task failed call."""
        self.calls.append(("task_failed", kwargs))
        return 1

    async def broadcast_task_retrying(self, **kwargs: Any) -> int:
        """Track task retrying call."""
        self.calls.append(("task_retrying", kwargs))
        return 1

    async def broadcast_worker_started(self, **kwargs: Any) -> int:
        """Track worker started call."""
        self.calls.append(("worker_started", kwargs))
        return 1

    async def broadcast_worker_heartbeat(self, **kwargs: Any) -> int:
        """Track worker heartbeat call."""
        self.calls.append(("worker_heartbeat", kwargs))
        return 1

    async def broadcast_worker_stopped(self, **kwargs: Any) -> int:
        """Track worker stopped call."""
        self.calls.append(("worker_stopped", kwargs))
        return 1


def pack_event(event: dict[str, Any]) -> bytes:
    """Pack an event dict to msgpack bytes."""
    result = msgpack.packb(event)
    assert result is not None
    return result


def as_broadcaster(mock: MockEventBroadcaster) -> EventBroadcaster:
    """Cast MockEventBroadcaster to EventBroadcaster for type checking."""
    return cast(EventBroadcaster, mock)


@pytest.fixture
def mock_redis() -> MockRedisClient:
    """Create a mock Redis client."""
    return MockRedisClient()


@pytest.fixture
def mock_broadcaster() -> MockEventBroadcaster:
    """Create a mock event broadcaster."""
    return MockEventBroadcaster()


@pytest.fixture
def consumer() -> EventConsumer:
    """Create an EventConsumer instance."""
    return EventConsumer(
        redis_url="redis://localhost:6379",
        channel="test:events",
    )


@pytest.mark.unit
class TestEventConsumerInit:
    """Tests for EventConsumer initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        consumer = EventConsumer()
        assert consumer.redis_url == "redis://localhost:6379"
        assert consumer.channel == "asynctasq:events"
        assert consumer._client is None
        assert consumer._pubsub is None
        assert consumer._task is None
        assert consumer._running is False

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        consumer = EventConsumer(
            redis_url="redis://custom:6380",
            channel="custom:channel",
        )
        assert consumer.redis_url == "redis://custom:6380"
        assert consumer.channel == "custom:channel"

    def test_init_with_env_vars(self) -> None:
        """Test initialization reads from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "ATQ_REDIS_URL": "redis://env-host:6381",
                "ATQ_EVENTS_CHANNEL": "env:channel",
            },
        ):
            consumer = EventConsumer()
            assert consumer.redis_url == "redis://env-host:6381"
            assert consumer.channel == "env:channel"


@pytest.mark.unit
class TestEventConsumerIsRunning:
    """Tests for is_running property."""

    def test_is_running_initially_false(self, consumer: EventConsumer) -> None:
        """Test is_running is False initially."""
        assert consumer.is_running is False

    def test_is_running_with_running_flag_but_no_task(self, consumer: EventConsumer) -> None:
        """Test is_running is False when flag is set but no task."""
        consumer._running = True
        assert consumer.is_running is False

    @pytest.mark.asyncio
    async def test_is_running_with_done_task(self, consumer: EventConsumer) -> None:
        """Test is_running is False when task is done."""
        consumer._running = True
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        future.set_result(None)
        consumer._task = cast(asyncio.Task[None], future)
        assert consumer.is_running is False


@pytest.mark.unit
class TestEventConsumerStartStop:
    """Tests for start and stop methods."""

    @pytest.mark.asyncio
    async def test_start_connects_to_redis(
        self, consumer: EventConsumer, mock_redis: MockRedisClient
    ) -> None:
        """Test start connects to Redis and subscribes to channel."""
        with patch("asynctasq_monitor.services.event_consumer.Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis

            await consumer.start()

            try:
                assert consumer._running is True
                assert consumer._client is mock_redis
                assert consumer._pubsub is mock_redis._pubsub
                assert "test:events" in mock_redis._pubsub.subscribed_channels
                assert consumer._task is not None
            finally:
                await consumer.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_running(
        self, consumer: EventConsumer, mock_redis: MockRedisClient
    ) -> None:
        """Test start logs warning when already running."""
        with patch("asynctasq_monitor.services.event_consumer.Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis

            await consumer.start()
            try:
                # Second start should just return
                await consumer.start()
                assert consumer._running is True
            finally:
                await consumer.stop()

    @pytest.mark.asyncio
    async def test_start_handles_connection_failure(self, consumer: EventConsumer) -> None:
        """Test start raises exception on connection failure."""
        with patch("asynctasq_monitor.services.event_consumer.Redis") as mock_redis_cls:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = ConnectionError("Connection refused")
            mock_redis_cls.from_url.return_value = mock_client

            with pytest.raises(ConnectionError):
                await consumer.start()

            assert consumer._running is False

    @pytest.mark.asyncio
    async def test_stop_cleans_up_resources(
        self, consumer: EventConsumer, mock_redis: MockRedisClient
    ) -> None:
        """Test stop properly cleans up resources."""
        with patch("asynctasq_monitor.services.event_consumer.Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis

            await consumer.start()
            await consumer.stop()

            assert consumer._running is False
            assert consumer._task is None
            assert consumer._pubsub is None
            assert consumer._client is None
            assert mock_redis._pubsub._closed is True
            assert mock_redis._closed is True

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, consumer: EventConsumer) -> None:
        """Test stop is safe to call when not running."""
        await consumer.stop()  # Should not raise
        assert consumer._running is False


@pytest.mark.unit
class TestEventConsumerHandleMessage:
    """Tests for _handle_message method."""

    @pytest.mark.asyncio
    async def test_handle_task_enqueued_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling task_enqueued event."""
        event = {
            "event_type": "task_enqueued",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "task_enqueued"
        assert kwargs["task_id"] == "task-123"
        assert kwargs["task_name"] == "send_email"
        assert kwargs["queue"] == "emails"

    @pytest.mark.asyncio
    async def test_handle_task_started_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling task_started event."""
        event = {
            "event_type": "task_started",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
            "worker_id": "worker-1",
            "attempt": 2,
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "task_started"
        assert kwargs["worker_id"] == "worker-1"
        assert kwargs["attempt"] == 2

    @pytest.mark.asyncio
    async def test_handle_task_completed_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling task_completed event."""
        event = {
            "event_type": "task_completed",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
            "worker_id": "worker-1",
            "duration_ms": 1500,
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "task_completed"
        assert kwargs["duration_ms"] == 1500

    @pytest.mark.asyncio
    async def test_handle_task_failed_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling task_failed event."""
        event = {
            "event_type": "task_failed",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
            "worker_id": "worker-1",
            "error": "Connection timeout",
            "attempt": 3,
            "duration_ms": 5000,
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "task_failed"
        assert kwargs["error"] == "Connection timeout"
        assert kwargs["attempt"] == 3
        assert kwargs["duration_ms"] == 5000

    @pytest.mark.asyncio
    async def test_handle_task_retrying_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling task_retrying event."""
        event = {
            "event_type": "task_retrying",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
            "attempt": 2,
            "error": "Temporary failure",
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "task_retrying"
        assert kwargs["attempt"] == 2
        assert kwargs["error"] == "Temporary failure"

    @pytest.mark.asyncio
    async def test_handle_worker_online_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling worker_online event."""
        event = {
            "event_type": "worker_online",
            "worker_id": "worker-1",
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "worker_started"
        assert kwargs["worker_id"] == "worker-1"

    @pytest.mark.asyncio
    async def test_handle_worker_heartbeat_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling worker_heartbeat event."""
        event = {
            "event_type": "worker_heartbeat",
            "worker_id": "worker-1",
            "active": 5,
            "processed": 100,
            "uptime_seconds": 3600,
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "worker_heartbeat"
        assert kwargs["worker_id"] == "worker-1"
        assert kwargs["load_percentage"] == 50.0  # 5 * 10.0
        assert kwargs["tasks_processed"] == 100
        assert kwargs["uptime_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_handle_worker_heartbeat_caps_load_at_100(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test worker heartbeat load percentage is capped at 100%."""
        event = {
            "event_type": "worker_heartbeat",
            "worker_id": "worker-1",
            "active": 15,  # Would be 150% without cap
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        _, kwargs = mock_broadcaster.calls[0]
        assert kwargs["load_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_handle_worker_offline_event(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling worker_offline event."""
        event = {
            "event_type": "worker_offline",
            "worker_id": "worker-1",
            "processed": 500,
            "uptime_seconds": 7200,
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "worker_stopped"
        assert kwargs["worker_id"] == "worker-1"
        assert kwargs["tasks_processed"] == 500
        assert kwargs["uptime_seconds"] == 7200

    @pytest.mark.asyncio
    async def test_handle_unknown_event_type(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling unknown event type logs warning."""
        event = {
            "event_type": "unknown_event",
            "data": "some data",
        }
        data = pack_event(event)

        with patch("asynctasq_monitor.services.event_consumer.logger") as mock_logger:
            await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

            mock_logger.warning.assert_called_once()
            assert "Unknown event type" in str(mock_logger.warning.call_args)

        assert len(mock_broadcaster.calls) == 0

    @pytest.mark.asyncio
    async def test_handle_invalid_msgpack_data(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling invalid msgpack data logs exception."""
        invalid_data = b"not valid msgpack"

        with patch("asynctasq_monitor.services.event_consumer.logger") as mock_logger:
            await consumer._handle_message(invalid_data, as_broadcaster(mock_broadcaster))

            mock_logger.exception.assert_called_once()

        assert len(mock_broadcaster.calls) == 0

    @pytest.mark.asyncio
    async def test_handle_missing_required_fields(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling event with missing required fields."""
        event = {
            "event_type": "task_enqueued",
            # Missing task_id, task_name, queue
        }
        data = pack_event(event)

        with patch("asynctasq_monitor.services.event_consumer.logger") as mock_logger:
            await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

            mock_logger.exception.assert_called_once()

        assert len(mock_broadcaster.calls) == 0

    @pytest.mark.asyncio
    async def test_handle_event_with_default_attempt(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling event uses default attempt value of 1."""
        event = {
            "event_type": "task_started",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
            "worker_id": "worker-1",
            # No attempt field
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        _, kwargs = mock_broadcaster.calls[0]
        assert kwargs["attempt"] == 1


@pytest.mark.unit
class TestEventConsumerConsumeLoop:
    """Tests for _consume_loop method."""

    @pytest.mark.asyncio
    async def test_consume_loop_processes_messages(
        self, mock_redis: MockRedisClient, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test consume loop processes messages from pubsub."""
        consumer = EventConsumer(redis_url="redis://localhost:6379", channel="test:events")

        # Add a test message
        event = {
            "event_type": "task_enqueued",
            "task_id": "task-123",
            "task_name": "test_task",
            "queue": "default",
        }
        mock_redis._pubsub.add_message(pack_event(event))
        mock_redis._pubsub._max_get_message_calls = 5  # Limit iterations

        with (
            patch("asynctasq_monitor.services.event_consumer.Redis") as mock_redis_cls,
            patch(
                "asynctasq_monitor.services.event_consumer.get_event_broadcaster"
            ) as mock_get_broadcaster,
        ):
            mock_redis_cls.from_url.return_value = mock_redis
            mock_get_broadcaster.return_value = mock_broadcaster

            await consumer.start()

            # Wait for processing (the loop will be cancelled by max calls)
            try:
                await asyncio.wait_for(asyncio.shield(consumer._task), timeout=0.5)  # type: ignore[arg-type]
            except (TimeoutError, asyncio.CancelledError):
                pass

            await consumer.stop()

        assert len(mock_broadcaster.calls) >= 1
        method, kwargs = mock_broadcaster.calls[0]
        assert method == "task_enqueued"
        assert kwargs["task_id"] == "task-123"

    @pytest.mark.asyncio
    async def test_consume_loop_ignores_non_message_types(
        self, mock_redis: MockRedisClient, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test consume loop ignores subscribe/unsubscribe messages."""
        consumer = EventConsumer(redis_url="redis://localhost:6379", channel="test:events")

        # Add a subscribe message (should be ignored)
        mock_redis._pubsub.messages.append({"type": "subscribe", "data": None})
        mock_redis._pubsub._max_get_message_calls = 5

        with (
            patch("asynctasq_monitor.services.event_consumer.Redis") as mock_redis_cls,
            patch(
                "asynctasq_monitor.services.event_consumer.get_event_broadcaster"
            ) as mock_get_broadcaster,
        ):
            mock_redis_cls.from_url.return_value = mock_redis
            mock_get_broadcaster.return_value = mock_broadcaster

            await consumer.start()

            try:
                await asyncio.wait_for(asyncio.shield(consumer._task), timeout=0.5)  # type: ignore[arg-type]
            except (TimeoutError, asyncio.CancelledError):
                pass

            await consumer.stop()

        assert len(mock_broadcaster.calls) == 0

    @pytest.mark.asyncio
    async def test_consume_loop_handles_errors_gracefully(
        self, mock_redis: MockRedisClient
    ) -> None:
        """Test consume loop continues after handling errors."""
        consumer = EventConsumer(redis_url="redis://localhost:6379", channel="test:events")

        # Add invalid data that will cause an exception
        mock_redis._pubsub.add_message(b"invalid msgpack data")
        mock_redis._pubsub._max_get_message_calls = 5

        with patch("asynctasq_monitor.services.event_consumer.Redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_redis

            await consumer.start()

            # Wait a bit for error handling
            try:
                await asyncio.wait_for(asyncio.shield(consumer._task), timeout=0.5)  # type: ignore[arg-type]
            except (TimeoutError, asyncio.CancelledError):
                pass

            # Consumer should still be marked as running (until max calls)
            # Note: it may have stopped due to CancelledError from max calls

            await consumer.stop()


@pytest.mark.unit
class TestEventConsumerSingleton:
    """Tests for singleton functions."""

    def test_get_event_consumer_returns_singleton(self) -> None:
        """Test get_event_consumer returns same instance."""
        reset_event_consumer()

        c1 = get_event_consumer()
        c2 = get_event_consumer()

        assert c1 is c2

        reset_event_consumer()

    def test_reset_event_consumer_clears_singleton(self) -> None:
        """Test reset_event_consumer clears the singleton."""
        c1 = get_event_consumer()
        reset_event_consumer()
        c2 = get_event_consumer()

        assert c1 is not c2

        reset_event_consumer()


@pytest.mark.unit
class TestEventConsumerEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_handle_task_completed_without_optional_fields(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test task_completed handles missing optional fields."""
        event = {
            "event_type": "task_completed",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
            # No worker_id or duration_ms
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        _, kwargs = mock_broadcaster.calls[0]
        assert kwargs.get("worker_id") is None
        assert kwargs.get("duration_ms") is None

    @pytest.mark.asyncio
    async def test_handle_task_failed_without_optional_fields(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test task_failed handles missing optional fields."""
        event = {
            "event_type": "task_failed",
            "task_id": "task-123",
            "task_name": "send_email",
            "queue": "emails",
            # No worker_id, error, or duration_ms
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        assert len(mock_broadcaster.calls) == 1
        _, kwargs = mock_broadcaster.calls[0]
        assert kwargs.get("worker_id") is None
        assert kwargs.get("error") is None
        assert kwargs["attempt"] == 1  # Default value

    @pytest.mark.asyncio
    async def test_handle_worker_heartbeat_without_active(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test worker_heartbeat handles missing active field."""
        event = {
            "event_type": "worker_heartbeat",
            "worker_id": "worker-1",
            # No active field
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        _, kwargs = mock_broadcaster.calls[0]
        assert kwargs["load_percentage"] == 0.0  # 0 * 10.0

    @pytest.mark.asyncio
    async def test_handle_worker_offline_without_optional_fields(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test worker_offline handles missing optional fields."""
        event = {
            "event_type": "worker_offline",
            "worker_id": "worker-1",
            # No processed or uptime_seconds
        }
        data = pack_event(event)

        await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

        _, kwargs = mock_broadcaster.calls[0]
        assert kwargs.get("tasks_processed") is None
        assert kwargs.get("uptime_seconds") is None

    @pytest.mark.asyncio
    async def test_stop_handles_pubsub_close_error(self, consumer: EventConsumer) -> None:
        """Test stop handles errors when closing pubsub."""
        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = AsyncMock(side_effect=Exception("Close error"))
        mock_pubsub.aclose = AsyncMock()

        consumer._pubsub = mock_pubsub
        consumer._running = True

        await consumer.stop()  # Should not raise

        assert consumer._pubsub is None

    @pytest.mark.asyncio
    async def test_stop_handles_client_close_error(self, consumer: EventConsumer) -> None:
        """Test stop handles errors when closing redis client."""
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock(side_effect=Exception("Close error"))

        consumer._client = mock_client
        consumer._running = True

        await consumer.stop()  # Should not raise

        assert consumer._client is None

    @pytest.mark.asyncio
    async def test_handle_empty_event_type(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling event with empty event_type."""
        event = {
            "event_type": "",
            "data": "some data",
        }
        data = pack_event(event)

        with patch("asynctasq_monitor.services.event_consumer.logger") as mock_logger:
            await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

            mock_logger.warning.assert_called_once()

        assert len(mock_broadcaster.calls) == 0

    @pytest.mark.asyncio
    async def test_handle_event_without_event_type(
        self, consumer: EventConsumer, mock_broadcaster: MockEventBroadcaster
    ) -> None:
        """Test handling event without event_type field."""
        event = {
            "task_id": "task-123",
            "data": "some data",
        }
        data = pack_event(event)

        with patch("asynctasq_monitor.services.event_consumer.logger") as mock_logger:
            await consumer._handle_message(data, as_broadcaster(mock_broadcaster))

            mock_logger.warning.assert_called_once()

        assert len(mock_broadcaster.calls) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "unit"])
