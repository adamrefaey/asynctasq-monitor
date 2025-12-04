"""Tests for EventBroadcaster service.

Following pytest best practices:
- Use explicit @pytest.mark.asyncio decorators (strict mode)
- Use pytest.mark.unit for categorization
- Mock the connection manager for isolation
"""

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock

import pytest

from async_task_q_monitor.websocket.broadcaster import (
    EventBroadcaster,
    get_event_broadcaster,
    set_event_broadcaster,
)

if TYPE_CHECKING:
    from async_task_q_monitor.websocket.manager import ConnectionManager


class MockConnectionManager:
    """Mock ConnectionManager for testing EventBroadcaster."""

    def __init__(self) -> None:
        """Initialize mock manager."""
        self.broadcast_calls: list[tuple[list[str], dict[str, Any]]] = []
        self.broadcast_to_rooms = AsyncMock(side_effect=self._track_broadcast)

    async def _track_broadcast(self, rooms: list[str], message: Any) -> int:
        """Track broadcast calls for verification."""
        # Convert Pydantic model to dict if needed
        if hasattr(message, "model_dump"):
            data = message.model_dump(mode="json")
        else:
            data = message
        self.broadcast_calls.append((list(rooms), data))
        return len(rooms)


@pytest.fixture
def mock_manager() -> MockConnectionManager:
    """Create a mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def broadcaster(mock_manager: MockConnectionManager) -> EventBroadcaster:
    """Create an EventBroadcaster with mock manager."""
    return EventBroadcaster(connection_manager=cast("ConnectionManager", mock_manager))


@pytest.mark.unit
class TestEventBroadcasterTaskEvents:
    """Tests for task event broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_task_enqueued(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting task enqueued event."""
        await broadcaster.broadcast_task_enqueued(
            task_id="abc123",
            task_name="send_email",
            queue="emails",
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert "global" in rooms
        assert "tasks" in rooms
        assert "queue:emails" in rooms
        assert data["type"] == "task_enqueued"
        assert data["task_id"] == "abc123"
        assert data["task_name"] == "send_email"
        assert data["queue"] == "emails"

    @pytest.mark.asyncio
    async def test_broadcast_task_started(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting task started event."""
        await broadcaster.broadcast_task_started(
            task_id="abc123",
            task_name="send_email",
            queue="emails",
            worker_id="worker-1",
            attempt=2,
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert "global" in rooms
        assert "tasks" in rooms
        assert "task:abc123" in rooms
        assert "queue:emails" in rooms
        assert "worker:worker-1" in rooms
        assert data["type"] == "task_started"
        assert data["worker_id"] == "worker-1"
        assert data["attempt"] == 2

    @pytest.mark.asyncio
    async def test_broadcast_task_completed(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting task completed event."""
        await broadcaster.broadcast_task_completed(
            task_id="abc123",
            task_name="send_email",
            queue="emails",
            worker_id="worker-1",
            duration_ms=2150,
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert "global" in rooms
        assert "tasks" in rooms
        assert "task:abc123" in rooms
        assert "worker:worker-1" in rooms
        assert data["type"] == "task_completed"
        assert data["duration_ms"] == 2150

    @pytest.mark.asyncio
    async def test_broadcast_task_failed(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting task failed event."""
        await broadcaster.broadcast_task_failed(
            task_id="abc123",
            task_name="process_order",
            queue="orders",
            worker_id="worker-2",
            error="Database connection failed",
            attempt=3,
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert data["type"] == "task_failed"
        assert data["error"] == "Database connection failed"
        assert data["attempt"] == 3

    @pytest.mark.asyncio
    async def test_broadcast_task_retrying(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting task retrying event."""
        await broadcaster.broadcast_task_retrying(
            task_id="abc123",
            task_name="send_notification",
            queue="notifications",
            attempt=2,
            error="Timeout",
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert data["type"] == "task_retrying"
        assert data["attempt"] == 2
        assert data["error"] == "Timeout"


@pytest.mark.unit
class TestEventBroadcasterWorkerEvents:
    """Tests for worker event broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_worker_started(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting worker started event."""
        await broadcaster.broadcast_worker_started(worker_id="worker-1")

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert "global" in rooms
        assert "workers" in rooms
        assert "worker:worker-1" in rooms
        assert data["type"] == "worker_started"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_broadcast_worker_stopped(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting worker stopped event."""
        await broadcaster.broadcast_worker_stopped(
            worker_id="worker-1",
            tasks_processed=1234,
            uptime_seconds=3600,
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert data["type"] == "worker_stopped"
        assert data["status"] == "down"
        assert data["tasks_processed"] == 1234
        assert data["uptime_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_broadcast_worker_heartbeat(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting worker heartbeat event."""
        await broadcaster.broadcast_worker_heartbeat(
            worker_id="worker-1",
            load_percentage=75.5,
            current_task_id="task-abc",
            tasks_processed=500,
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        # Heartbeat doesn't go to global (too frequent)
        assert "global" not in rooms
        assert "workers" in rooms
        assert "worker:worker-1" in rooms
        assert data["type"] == "worker_heartbeat"
        assert data["load_percentage"] == 75.5


@pytest.mark.unit
class TestEventBroadcasterQueueEvents:
    """Tests for queue event broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_queue_depth_changed(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting queue depth changed event."""
        await broadcaster.broadcast_queue_depth_changed(
            queue_name="emails",
            depth=150,
            processing=5,
            throughput_per_minute=45.2,
        )

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert "global" in rooms
        assert "queues" in rooms
        assert "queue:emails" in rooms
        assert data["type"] == "queue_depth_changed"
        assert data["depth"] == 150
        assert data["processing"] == 5

    @pytest.mark.asyncio
    async def test_broadcast_queue_paused(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting queue paused event."""
        await broadcaster.broadcast_queue_paused(queue_name="orders")

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert data["type"] == "queue_paused"
        assert data["queue_name"] == "orders"

    @pytest.mark.asyncio
    async def test_broadcast_queue_resumed(
        self,
        broadcaster: EventBroadcaster,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test broadcasting queue resumed event."""
        await broadcaster.broadcast_queue_resumed(queue_name="orders")

        assert len(mock_manager.broadcast_calls) == 1
        rooms, data = mock_manager.broadcast_calls[0]

        assert data["type"] == "queue_resumed"


@pytest.mark.unit
class TestEventBroadcasterSingleton:
    """Tests for EventBroadcaster singleton functions."""

    def test_get_event_broadcaster_returns_singleton(self) -> None:
        """Test get_event_broadcaster returns same instance."""
        # Reset singleton
        set_event_broadcaster(None)

        b1 = get_event_broadcaster()
        b2 = get_event_broadcaster()

        assert b1 is b2

        # Cleanup
        set_event_broadcaster(None)

    def test_set_event_broadcaster(self) -> None:
        """Test set_event_broadcaster replaces singleton."""
        custom = EventBroadcaster()
        set_event_broadcaster(custom)

        retrieved = get_event_broadcaster()

        assert retrieved is custom

        # Cleanup
        set_event_broadcaster(None)


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "unit"])
