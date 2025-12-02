"""Tests for WebSocket ConnectionManager.

Following pytest best practices:
- Use explicit @pytest.mark.asyncio decorators (strict mode)
- Use pytest.mark.unit for categorization
- Use fixtures for reusable test data
- Mock WebSocket connections properly
"""

import asyncio
from typing import Any, cast

from fastapi import WebSocket
from fastapi.websockets import WebSocketState
import pytest

from async_task_q_monitor.websocket.manager import (
    ConnectionManager,
    get_connection_manager,
    set_connection_manager,
)


class MockWebSocket:
    """Mock WebSocket for testing.

    This mock simulates the FastAPI WebSocket interface.
    """

    def __init__(self, client_state: WebSocketState | None = None) -> None:
        """Initialize mock WebSocket."""
        self.client_state = client_state or WebSocketState.CONNECTED
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.sent_messages: list[dict[str, Any]] = []

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        self.accepted = True

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the WebSocket connection."""
        self.closed = True
        self.close_code = code
        self.client_state = WebSocketState.DISCONNECTED

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON data."""
        if self.client_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket not connected")
        self.sent_messages.append(data)

    def as_websocket(self) -> WebSocket:
        """Cast this mock to WebSocket type for type checking."""
        return cast(WebSocket, self)


@pytest.fixture
def manager() -> ConnectionManager:
    """Create a fresh ConnectionManager for testing."""
    return ConnectionManager()


@pytest.mark.unit
class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.mark.asyncio
    async def test_connect_default_room(self, manager: ConnectionManager) -> None:
        """Test connecting subscribes to 'global' room by default."""
        ws = MockWebSocket()

        await manager.connect(ws.as_websocket())

        assert ws.accepted is True
        assert manager.active_connections_count == 1
        assert "global" in manager.get_rooms_for_connection(ws.as_websocket())

    @pytest.mark.asyncio
    async def test_connect_custom_rooms(self, manager: ConnectionManager) -> None:
        """Test connecting with custom room subscriptions."""
        ws = MockWebSocket()

        await manager.connect(ws.as_websocket(), rooms=["tasks", "workers", "queue:emails"])

        assert ws.accepted is True
        rooms = manager.get_rooms_for_connection(ws.as_websocket())
        assert "tasks" in rooms
        assert "workers" in rooms
        assert "queue:emails" in rooms
        assert "global" not in rooms

    @pytest.mark.asyncio
    async def test_disconnect(self, manager: ConnectionManager) -> None:
        """Test disconnecting removes from all rooms."""
        ws = MockWebSocket()
        await manager.connect(ws.as_websocket(), rooms=["tasks", "workers"])

        await manager.disconnect(ws.as_websocket())

        assert manager.active_connections_count == 0
        assert manager.get_rooms_for_connection(ws.as_websocket()) == set()
        assert manager.get_connections_in_room("tasks") == 0
        assert manager.get_connections_in_room("workers") == 0

    @pytest.mark.asyncio
    async def test_subscribe_additional_room(self, manager: ConnectionManager) -> None:
        """Test subscribing to additional rooms after connection."""
        ws = MockWebSocket()
        await manager.connect(ws.as_websocket())

        await manager.subscribe(ws.as_websocket(), "task:abc123")

        rooms = manager.get_rooms_for_connection(ws.as_websocket())
        assert "global" in rooms
        assert "task:abc123" in rooms

    @pytest.mark.asyncio
    async def test_unsubscribe_from_room(self, manager: ConnectionManager) -> None:
        """Test unsubscribing from a room."""
        ws = MockWebSocket()
        await manager.connect(ws.as_websocket(), rooms=["tasks", "workers"])

        await manager.unsubscribe(ws.as_websocket(), "tasks")

        rooms = manager.get_rooms_for_connection(ws.as_websocket())
        assert "tasks" not in rooms
        assert "workers" in rooms

    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, manager: ConnectionManager) -> None:
        """Test broadcasting to a specific room."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1.as_websocket(), rooms=["tasks"])
        await manager.connect(ws2.as_websocket(), rooms=["tasks"])
        await manager.connect(ws3.as_websocket(), rooms=["workers"])

        message = {"type": "test", "data": "hello"}
        count = await manager.broadcast_to_room("tasks", message)

        assert count == 2
        assert message in ws1.sent_messages
        assert message in ws2.sent_messages
        assert message not in ws3.sent_messages

    @pytest.mark.asyncio
    async def test_broadcast_to_rooms_deduplication(self, manager: ConnectionManager) -> None:
        """Test broadcasting to multiple rooms deduplicates recipients."""
        ws = MockWebSocket()
        await manager.connect(ws.as_websocket(), rooms=["tasks", "workers"])

        message = {"type": "test"}
        count = await manager.broadcast_to_rooms(["tasks", "workers"], message)

        # Should only receive once even though in both rooms
        assert count == 1
        assert len(ws.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_broadcast_all(self, manager: ConnectionManager) -> None:
        """Test broadcasting to all connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1.as_websocket(), rooms=["tasks"])
        await manager.connect(ws2.as_websocket(), rooms=["workers"])

        message = {"type": "global_update"}
        count = await manager.broadcast_all(message)

        assert count == 2
        assert message in ws1.sent_messages
        assert message in ws2.sent_messages

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager: ConnectionManager) -> None:
        """Test sending message to specific client."""
        ws = MockWebSocket()
        await manager.connect(ws.as_websocket())

        message = {"type": "personal"}
        success = await manager.send_personal_message(ws.as_websocket(), message)

        assert success is True
        assert message in ws.sent_messages

    @pytest.mark.asyncio
    async def test_send_to_disconnected_client(self, manager: ConnectionManager) -> None:
        """Test sending to disconnected client returns False."""
        ws = MockWebSocket(client_state=WebSocketState.DISCONNECTED)

        success = await manager.send_personal_message(ws.as_websocket(), {"type": "test"})

        assert success is False

    @pytest.mark.asyncio
    async def test_room_counts(self, manager: ConnectionManager) -> None:
        """Test room_counts property."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()

        await manager.connect(ws1.as_websocket(), rooms=["tasks"])
        await manager.connect(ws2.as_websocket(), rooms=["tasks", "workers"])
        await manager.connect(ws3.as_websocket(), rooms=["workers"])

        counts = manager.room_counts

        assert counts["tasks"] == 2
        assert counts["workers"] == 2

    @pytest.mark.asyncio
    async def test_pydantic_model_serialization(self, manager: ConnectionManager) -> None:
        """Test broadcasting Pydantic models serializes correctly."""
        from async_task_q_monitor.websocket.events import (
            MetricsEvent,
            WebSocketEventType,
        )

        ws = MockWebSocket()
        await manager.connect(ws.as_websocket())

        event = MetricsEvent(
            type=WebSocketEventType.METRICS_UPDATED,
            pending=10,
            running=2,
        )
        await manager.broadcast_to_room("global", event)

        assert len(ws.sent_messages) == 1
        sent = ws.sent_messages[0]
        assert sent["type"] == "metrics_updated"
        assert sent["pending"] == 10
        assert sent["running"] == 2


@pytest.mark.unit
class TestConnectionManagerSingleton:
    """Tests for ConnectionManager singleton functions."""

    def test_get_connection_manager_returns_singleton(self) -> None:
        """Test get_connection_manager returns same instance."""
        # Reset singleton
        set_connection_manager(None)

        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2

    def test_set_connection_manager(self) -> None:
        """Test set_connection_manager replaces singleton."""
        custom_manager = ConnectionManager()
        set_connection_manager(custom_manager)

        retrieved = get_connection_manager()

        assert retrieved is custom_manager

        # Cleanup
        set_connection_manager(None)


@pytest.mark.unit
class TestConnectionManagerConcurrency:
    """Tests for ConnectionManager thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_connects(self, manager: ConnectionManager) -> None:
        """Test concurrent connections are handled safely."""
        websockets = [MockWebSocket() for _ in range(10)]

        # Connect all concurrently
        await asyncio.gather(
            *[manager.connect(ws.as_websocket(), rooms=["global"]) for ws in websockets]
        )

        assert manager.active_connections_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_broadcasts(self, manager: ConnectionManager) -> None:
        """Test concurrent broadcasts don't cause issues."""
        websockets = [MockWebSocket() for _ in range(5)]
        for ws in websockets:
            await manager.connect(ws.as_websocket(), rooms=["global"])

        messages = [{"type": "test", "id": i} for i in range(10)]

        # Broadcast all concurrently
        results = await asyncio.gather(
            *[manager.broadcast_to_room("global", msg) for msg in messages]
        )

        # Each broadcast should reach all 5 clients
        assert all(r == 5 for r in results)

        # Each client should have received all 10 messages
        for ws in websockets:
            assert len(ws.sent_messages) == 10
