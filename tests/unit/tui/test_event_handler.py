"""Tests for TUI event handler.

Tests for the real-time event streaming and metrics tracking functionality.
"""

from __future__ import annotations

from time import monotonic
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
import pytest

from asynctasq_monitor.tui.event_handler import (
    ConnectionStatusChanged,
    EventReceived,
    MetricsTracker,
    TUIEvent,
    TUIEventConsumer,
    TUIEventType,
)


class TestTUIEventType:
    """Tests for TUIEventType enum."""

    @pytest.mark.unit
    def test_task_event_types(self) -> None:
        """Test task-related event types."""
        assert TUIEventType.TASK_ENQUEUED.value == "task_enqueued"
        assert TUIEventType.TASK_STARTED.value == "task_started"
        assert TUIEventType.TASK_COMPLETED.value == "task_completed"
        assert TUIEventType.TASK_FAILED.value == "task_failed"
        assert TUIEventType.TASK_RETRYING.value == "task_retrying"

    @pytest.mark.unit
    def test_worker_event_types(self) -> None:
        """Test worker-related event types."""
        assert TUIEventType.WORKER_ONLINE.value == "worker_online"
        assert TUIEventType.WORKER_HEARTBEAT.value == "worker_heartbeat"
        assert TUIEventType.WORKER_OFFLINE.value == "worker_offline"


class TestTUIEvent:
    """Tests for TUIEvent dataclass."""

    @pytest.mark.unit
    def test_event_creation(self) -> None:
        """Test creating a TUI event."""
        data = {
            "task_id": "abc123",
            "task_name": "send_email",
            "queue": "default",
            "worker_id": "worker-1",
        }
        event = TUIEvent(type=TUIEventType.TASK_STARTED, data=data)

        assert event.type == TUIEventType.TASK_STARTED
        assert event.task_id == "abc123"
        assert event.task_name == "send_email"
        assert event.queue == "default"
        assert event.worker_id == "worker-1"

    @pytest.mark.unit
    def test_event_missing_fields(self) -> None:
        """Test event with missing optional fields."""
        event = TUIEvent(type=TUIEventType.TASK_ENQUEUED, data={})

        assert event.task_id is None
        assert event.task_name is None
        assert event.queue is None
        assert event.worker_id is None


class TestEventReceivedMessage:
    """Tests for EventReceived message."""

    @pytest.mark.unit
    def test_message_creation(self) -> None:
        """Test creating an EventReceived message."""
        event = TUIEvent(
            type=TUIEventType.TASK_COMPLETED,
            data={"task_id": "test123"},
        )
        message = EventReceived(event)

        assert message.event is event
        assert message.event.type == TUIEventType.TASK_COMPLETED


class TestConnectionStatusChangedMessage:
    """Tests for ConnectionStatusChanged message."""

    @pytest.mark.unit
    def test_connected_status(self) -> None:
        """Test connected status message."""
        message = ConnectionStatusChanged(connected=True)

        assert message.connected is True
        assert message.error is None

    @pytest.mark.unit
    def test_disconnected_with_error(self) -> None:
        """Test disconnected status with error."""
        message = ConnectionStatusChanged(connected=False, error="Connection refused")

        assert message.connected is False
        assert message.error == "Connection refused"


class TestMetricsTracker:
    """Tests for MetricsTracker class."""

    @pytest.mark.unit
    def test_initial_state(self) -> None:
        """Test initial metrics state."""
        tracker = MetricsTracker()

        assert tracker.pending == 0
        assert tracker.running == 0
        assert tracker.completed == 0
        assert tracker.failed == 0
        assert tracker.throughput_history == []

    @pytest.mark.unit
    def test_handle_task_enqueued(self) -> None:
        """Test handling task enqueued event."""
        tracker = MetricsTracker()
        event = TUIEvent(type=TUIEventType.TASK_ENQUEUED, data={})

        tracker.handle_event(event)

        assert tracker.pending == 1
        assert tracker.running == 0

    @pytest.mark.unit
    def test_handle_task_started(self) -> None:
        """Test handling task started event."""
        tracker = MetricsTracker()
        tracker.pending = 5

        event = TUIEvent(type=TUIEventType.TASK_STARTED, data={})
        tracker.handle_event(event)

        assert tracker.pending == 4
        assert tracker.running == 1

    @pytest.mark.unit
    def test_handle_task_started_prevents_negative(self) -> None:
        """Test that pending count doesn't go negative."""
        tracker = MetricsTracker()
        tracker.pending = 0

        event = TUIEvent(type=TUIEventType.TASK_STARTED, data={})
        tracker.handle_event(event)

        assert tracker.pending == 0
        assert tracker.running == 1

    @pytest.mark.unit
    def test_handle_task_completed(self) -> None:
        """Test handling task completed event."""
        tracker = MetricsTracker()
        tracker.running = 3

        event = TUIEvent(type=TUIEventType.TASK_COMPLETED, data={})
        tracker.handle_event(event)

        assert tracker.running == 2
        assert tracker.completed == 1

    @pytest.mark.unit
    def test_handle_task_failed(self) -> None:
        """Test handling task failed event."""
        tracker = MetricsTracker()
        tracker.running = 2

        event = TUIEvent(type=TUIEventType.TASK_FAILED, data={})
        tracker.handle_event(event)

        assert tracker.running == 1
        assert tracker.failed == 1

    @pytest.mark.unit
    def test_handle_task_retrying(self) -> None:
        """Test handling task retrying event."""
        tracker = MetricsTracker()
        tracker.running = 1

        event = TUIEvent(type=TUIEventType.TASK_RETRYING, data={})
        tracker.handle_event(event)

        assert tracker.running == 0
        assert tracker.pending == 1  # Goes back to pending

    @pytest.mark.unit
    def test_set_metrics(self) -> None:
        """Test setting metrics from external source."""
        tracker = MetricsTracker()

        tracker.set_metrics(pending=10, running=5, completed=100, failed=3)

        assert tracker.pending == 10
        assert tracker.running == 5
        assert tracker.completed == 100
        assert tracker.failed == 3

    @pytest.mark.unit
    def test_sample_throughput_first_call(self) -> None:
        """Test first throughput sample returns None."""
        tracker = MetricsTracker()

        result = tracker.sample_throughput(monotonic())

        assert result is None

    @pytest.mark.unit
    def test_sample_throughput_calculation(self) -> None:
        """Test throughput calculation between samples."""
        tracker = MetricsTracker()
        tracker.completed = 0

        # First sample
        time1 = 0.0
        tracker.sample_throughput(time1)

        # Simulate 10 completed tasks
        tracker.completed = 10

        # Second sample after 60 seconds
        time2 = 60.0
        result = tracker.sample_throughput(time2)

        # 10 tasks in 60 seconds = 10 tasks/minute
        assert result is not None
        assert result == pytest.approx(10.0, rel=0.01)

    @pytest.mark.unit
    def test_sample_throughput_history_limit(self) -> None:
        """Test that throughput history is limited to 60 samples."""
        tracker = MetricsTracker()
        tracker.completed = 0

        # First sample
        current_time = 0.0
        tracker.sample_throughput(current_time)

        # Generate 70 samples
        for _ in range(70):
            current_time += 2.0  # 2 seconds between samples
            tracker.completed += 1
            tracker.sample_throughput(current_time)

        # Should keep only last 60
        assert len(tracker.throughput_history) == 60

    @pytest.mark.unit
    def test_sample_throughput_min_interval(self) -> None:
        """Test that samples too close together are skipped."""
        tracker = MetricsTracker()
        tracker.completed = 0

        # First sample
        time1 = 0.0
        tracker.sample_throughput(time1)
        tracker.completed = 10

        # Try to sample again immediately
        time2 = 0.5  # Only 0.5 seconds later
        result = tracker.sample_throughput(time2)

        # Should return None because interval is too short
        assert result is None


class TestTUIEventConsumer:
    """Tests for TUIEventConsumer class."""

    @pytest.fixture
    def mock_app(self) -> MagicMock:
        """Create a mock Textual app."""
        app = MagicMock()
        app.post_message = MagicMock()
        return app

    @pytest.mark.unit
    def test_consumer_initialization(self, mock_app: MagicMock) -> None:
        """Test consumer initialization."""
        consumer = TUIEventConsumer(
            app=mock_app,
            redis_url="redis://localhost:6379",
            channel="test:events",
        )

        assert consumer.app is mock_app
        assert consumer.redis_url == "redis://localhost:6379"
        assert consumer.channel == "test:events"
        assert consumer.is_running is False

    @pytest.mark.unit
    def test_is_running_false_initially(self, mock_app: MagicMock) -> None:
        """Test is_running property when not started."""
        consumer = TUIEventConsumer(app=mock_app)

        assert consumer.is_running is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_message_task_enqueued(self, mock_app: MagicMock) -> None:
        """Test handling a task enqueued message."""
        consumer = TUIEventConsumer(app=mock_app)

        event_data = {
            "event_type": "task_enqueued",
            "task_id": "abc123",
            "task_name": "send_email",
            "queue": "default",
        }
        data = msgpack.packb(event_data)
        assert data is not None

        await consumer._handle_message(data)

        # Verify message was posted
        mock_app.post_message.assert_called_once()
        call_args = mock_app.post_message.call_args
        message = call_args[0][0]

        assert isinstance(message, EventReceived)
        assert message.event.type == TUIEventType.TASK_ENQUEUED
        assert message.event.task_id == "abc123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_message_worker_online(self, mock_app: MagicMock) -> None:
        """Test handling a worker online message."""
        consumer = TUIEventConsumer(app=mock_app)

        event_data = {
            "event_type": "worker_online",
            "worker_id": "worker-1",
        }
        data = msgpack.packb(event_data)
        assert data is not None

        await consumer._handle_message(data)

        mock_app.post_message.assert_called_once()
        message = mock_app.post_message.call_args[0][0]

        assert isinstance(message, EventReceived)
        assert message.event.type == TUIEventType.WORKER_ONLINE
        assert message.event.worker_id == "worker-1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_message_unknown_type(self, mock_app: MagicMock) -> None:
        """Test handling an unknown event type."""
        consumer = TUIEventConsumer(app=mock_app)

        event_data = {
            "event_type": "unknown_event",
            "task_id": "abc123",
        }
        data = msgpack.packb(event_data)
        assert data is not None

        await consumer._handle_message(data)

        # Unknown events should not post a message
        mock_app.post_message.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handle_message_invalid_msgpack(self, mock_app: MagicMock) -> None:
        """Test handling invalid msgpack data."""
        consumer = TUIEventConsumer(app=mock_app)

        # Invalid msgpack data
        data = b"not valid msgpack"

        # Should not raise, just log error
        await consumer._handle_message(data)

        mock_app.post_message.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_posts_connected_status(self, mock_app: MagicMock) -> None:
        """Test that start posts a connected status."""
        consumer = TUIEventConsumer(app=mock_app)

        with (
            patch.object(consumer, "_client"),
            patch("asynctasq_monitor.tui.event_handler.Redis") as mock_redis_class,
        ):
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_pubsub = AsyncMock()
            mock_pubsub.subscribe = AsyncMock()
            # Make get_message return None so the loop keeps running
            mock_pubsub.get_message = AsyncMock(return_value=None)
            mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
            mock_redis_class.from_url = MagicMock(return_value=mock_redis)

            await consumer.start()

            # Verify connected status was posted
            calls = mock_app.post_message.call_args_list
            connected_call = next(
                (c for c in calls if isinstance(c[0][0], ConnectionStatusChanged)), None
            )
            assert connected_call is not None
            assert connected_call[0][0].connected is True

            # Cleanup - use the stop method for proper cleanup
            await consumer.stop()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_cleans_up_resources(self, mock_app: MagicMock) -> None:
        """Test that stop properly cleans up resources."""
        consumer = TUIEventConsumer(app=mock_app)
        consumer._running = True
        consumer._client = AsyncMock()
        consumer._client.aclose = AsyncMock()
        consumer._pubsub = AsyncMock()
        consumer._pubsub.unsubscribe = AsyncMock()
        consumer._pubsub.aclose = AsyncMock()
        consumer._task = None

        await consumer.stop()

        assert consumer._running is False
        assert consumer._client is None
        assert consumer._pubsub is None


class TestMetricsTrackerEventSequence:
    """Test realistic event sequences."""

    @pytest.mark.unit
    def test_full_task_lifecycle(self) -> None:
        """Test metrics through a complete task lifecycle."""
        tracker = MetricsTracker()

        # Task is enqueued
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_ENQUEUED, data={}))
        assert tracker.pending == 1

        # Task starts
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_STARTED, data={}))
        assert tracker.pending == 0
        assert tracker.running == 1

        # Task completes
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_COMPLETED, data={}))
        assert tracker.running == 0
        assert tracker.completed == 1

    @pytest.mark.unit
    def test_task_retry_lifecycle(self) -> None:
        """Test metrics when a task fails and retries."""
        tracker = MetricsTracker()

        # Task enqueued and started
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_ENQUEUED, data={}))
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_STARTED, data={}))

        # Task fails with retry
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_RETRYING, data={}))
        assert tracker.running == 0
        assert tracker.pending == 1  # Back in queue

        # Task restarts
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_STARTED, data={}))
        assert tracker.pending == 0
        assert tracker.running == 1

        # Task completes
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_COMPLETED, data={}))
        assert tracker.running == 0
        assert tracker.completed == 1

    @pytest.mark.unit
    def test_concurrent_tasks(self) -> None:
        """Test metrics with multiple concurrent tasks."""
        tracker = MetricsTracker()

        # Enqueue 5 tasks
        for _ in range(5):
            tracker.handle_event(TUIEvent(type=TUIEventType.TASK_ENQUEUED, data={}))
        assert tracker.pending == 5

        # Start 3 tasks
        for _ in range(3):
            tracker.handle_event(TUIEvent(type=TUIEventType.TASK_STARTED, data={}))
        assert tracker.pending == 2
        assert tracker.running == 3

        # 2 complete, 1 fails
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_COMPLETED, data={}))
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_COMPLETED, data={}))
        tracker.handle_event(TUIEvent(type=TUIEventType.TASK_FAILED, data={}))

        assert tracker.running == 0
        assert tracker.completed == 2
        assert tracker.failed == 1
