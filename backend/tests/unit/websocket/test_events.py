"""Tests for WebSocket event models.

Following pytest best practices:
- Use explicit @pytest.mark.asyncio decorators (strict mode)
- Use pytest.mark.unit for categorization
- Use parametrize for test variations
- Use fixtures for reusable test data
"""

from datetime import datetime
from typing import Literal

from pydantic import ValidationError
import pytest

from async_task_q_monitor.websocket.events import (
    MetricsEvent,
    QueueEvent,
    TaskEvent,
    WebSocketEventType,
    WorkerEvent,
)


@pytest.mark.unit
class TestTaskEvent:
    """Tests for TaskEvent model."""

    def test_task_event_creation(self) -> None:
        """Test creating a valid TaskEvent."""
        event = TaskEvent(
            type=WebSocketEventType.TASK_COMPLETED,
            task_id="abc-123",
            task_name="send_email",
            queue="emails",
            worker_id="worker-1",
            duration_ms=2150,
            status="completed",
            error=None,
            attempt=1,
        )

        assert event.type == WebSocketEventType.TASK_COMPLETED
        assert event.task_id == "abc-123"
        assert event.task_name == "send_email"
        assert event.queue == "emails"
        assert event.worker_id == "worker-1"
        assert event.duration_ms == 2150
        assert isinstance(event.timestamp, datetime)

    def test_task_event_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            TaskEvent(  # type: ignore[call-arg]
                type=WebSocketEventType.TASK_COMPLETED,
                # Missing task_id, task_name, queue
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 3
        error_locs = {e["loc"][0] for e in errors}
        assert "task_id" in error_locs
        assert "task_name" in error_locs
        assert "queue" in error_locs

    def test_task_event_json_serialization(self) -> None:
        """Test JSON serialization with model_dump."""
        event = TaskEvent(
            type=WebSocketEventType.TASK_FAILED,
            task_id="xyz-456",
            task_name="process_order",
            queue="orders",
            error="Connection timeout",
            attempt=3,
        )

        data = event.model_dump(mode="json")

        assert data["type"] == "task_failed"
        assert data["task_id"] == "xyz-456"
        assert data["error"] == "Connection timeout"
        assert data["attempt"] == 3
        assert "timestamp" in data

    @pytest.mark.parametrize(
        "event_type",
        [
            WebSocketEventType.TASK_ENQUEUED,
            WebSocketEventType.TASK_STARTED,
            WebSocketEventType.TASK_COMPLETED,
            WebSocketEventType.TASK_FAILED,
            WebSocketEventType.TASK_RETRYING,
            WebSocketEventType.TASK_CANCELLED,
        ],
    )
    def test_task_event_types(
        self,
        event_type: Literal[
            WebSocketEventType.TASK_ENQUEUED,
            WebSocketEventType.TASK_STARTED,
            WebSocketEventType.TASK_COMPLETED,
            WebSocketEventType.TASK_FAILED,
            WebSocketEventType.TASK_RETRYING,
            WebSocketEventType.TASK_CANCELLED,
        ],
    ) -> None:
        """Test all valid task event types."""
        event = TaskEvent(
            type=event_type,
            task_id="test-id",
            task_name="test_task",
            queue="test_queue",
        )
        assert event.type == event_type

    def test_task_event_immutable(self) -> None:
        """Test that TaskEvent is frozen (immutable)."""
        event = TaskEvent(
            type=WebSocketEventType.TASK_COMPLETED,
            task_id="abc-123",
            task_name="test",
            queue="test",
        )

        with pytest.raises(ValidationError):
            event.task_id = "new-id"


@pytest.mark.unit
class TestWorkerEvent:
    """Tests for WorkerEvent model."""

    def test_worker_event_creation(self) -> None:
        """Test creating a valid WorkerEvent."""
        event = WorkerEvent(
            type=WebSocketEventType.WORKER_HEARTBEAT,
            worker_id="worker-1",
            load_percentage=75.5,
            current_task_id="task-abc",
            tasks_processed=1234,
        )

        assert event.type == WebSocketEventType.WORKER_HEARTBEAT
        assert event.worker_id == "worker-1"
        assert event.load_percentage == 75.5
        assert event.current_task_id == "task-abc"
        assert event.tasks_processed == 1234

    def test_worker_event_load_percentage_validation(self) -> None:
        """Test load_percentage must be 0-100."""
        # Valid values
        event = WorkerEvent(
            type=WebSocketEventType.WORKER_HEARTBEAT,
            worker_id="worker-1",
            load_percentage=0,
        )
        assert event.load_percentage == 0

        event = WorkerEvent(
            type=WebSocketEventType.WORKER_HEARTBEAT,
            worker_id="worker-1",
            load_percentage=100,
        )
        assert event.load_percentage == 100

        # Invalid: negative
        with pytest.raises(ValidationError):
            WorkerEvent(
                type=WebSocketEventType.WORKER_HEARTBEAT,
                worker_id="worker-1",
                load_percentage=-1,
            )

        # Invalid: over 100
        with pytest.raises(ValidationError):
            WorkerEvent(
                type=WebSocketEventType.WORKER_HEARTBEAT,
                worker_id="worker-1",
                load_percentage=101,
            )


@pytest.mark.unit
class TestQueueEvent:
    """Tests for QueueEvent model."""

    def test_queue_event_creation(self) -> None:
        """Test creating a valid QueueEvent."""
        event = QueueEvent(
            type=WebSocketEventType.QUEUE_DEPTH_CHANGED,
            queue_name="emails",
            depth=150,
            processing=5,
            throughput_per_minute=45.2,
        )

        assert event.type == WebSocketEventType.QUEUE_DEPTH_CHANGED
        assert event.queue_name == "emails"
        assert event.depth == 150
        assert event.processing == 5
        assert event.throughput_per_minute == 45.2

    def test_queue_event_depth_non_negative(self) -> None:
        """Test that depth must be non-negative."""
        with pytest.raises(ValidationError):
            QueueEvent(
                type=WebSocketEventType.QUEUE_DEPTH_CHANGED,
                queue_name="test",
                depth=-1,
            )


@pytest.mark.unit
class TestMetricsEvent:
    """Tests for MetricsEvent model."""

    def test_metrics_event_creation(self) -> None:
        """Test creating a valid MetricsEvent."""
        event = MetricsEvent(
            pending=150,
            running=5,
            completed=10243,
            failed=87,
            success_rate=99.15,
            active_workers=3,
            queue_depths={"emails": 50, "orders": 100},
        )

        assert event.type == WebSocketEventType.METRICS_UPDATED
        assert event.pending == 150
        assert event.running == 5
        assert event.completed == 10243
        assert event.failed == 87
        assert event.success_rate == 99.15
        assert event.active_workers == 3
        assert event.queue_depths == {"emails": 50, "orders": 100}

    def test_metrics_event_defaults(self) -> None:
        """Test MetricsEvent default values."""
        event = MetricsEvent()

        assert event.type == WebSocketEventType.METRICS_UPDATED
        assert event.pending == 0
        assert event.running == 0
        assert event.completed == 0
        assert event.failed == 0
        assert event.success_rate is None
        assert event.active_workers == 0
        assert event.queue_depths == {}

    def test_metrics_event_json_schema(self) -> None:
        """Test MetricsEvent has proper JSON schema example."""
        schema = MetricsEvent.model_json_schema()

        assert "example" in schema
        example = schema["example"]
        assert "pending" in example
        assert "running" in example
        assert "completed" in example
        assert "failed" in example
