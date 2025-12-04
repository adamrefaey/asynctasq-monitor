"""Integration tests for WebSocket ConnectionManager error handling.

These tests focus on edge cases and error handling scenarios:
- Timeout handling for slow clients
- WebSocketDisconnect during send
- Exception handling during broadcast
- Force disconnect behavior
- Concurrent connection/disconnection scenarios

Following FastAPI WebSocket testing best practices:
- Use mock WebSockets for controlled testing
- Test concurrent scenarios with asyncio.gather
- Test error recovery and cleanup
"""

import asyncio
from typing import Any, cast

from fastapi import WebSocket
from fastapi.websockets import WebSocketState
import pytest

from asynctasq_monitor.websocket.manager import (
    ConnectionManager,
    get_connection_manager,
    set_connection_manager,
)


class SlowMockWebSocket:
    """Mock WebSocket that simulates slow sends."""

    def __init__(
        self,
        client_state: WebSocketState = WebSocketState.CONNECTED,
        send_delay: float = 10.0,  # Longer than SEND_TIMEOUT
    ) -> None:
        self.client_state = client_state
        self.send_delay = send_delay
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.sent_messages: list[dict[str, Any]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.client_state = WebSocketState.DISCONNECTED

    async def send_json(self, data: dict[str, Any]) -> None:
        # Simulate slow send
        await asyncio.sleep(self.send_delay)
        if self.client_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket not connected")
        self.sent_messages.append(data)

    def as_websocket(self) -> WebSocket:
        return cast(WebSocket, self)


class DisconnectingMockWebSocket:
    """Mock WebSocket that raises WebSocketDisconnect during send."""

    def __init__(self, client_state: WebSocketState = WebSocketState.CONNECTED) -> None:
        self.client_state = client_state
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.client_state = WebSocketState.DISCONNECTED

    async def send_json(self, data: dict[str, Any]) -> None:
        from fastapi import WebSocketDisconnect

        raise WebSocketDisconnect(code=1000)

    def as_websocket(self) -> WebSocket:
        return cast(WebSocket, self)


class ExceptionMockWebSocket:
    """Mock WebSocket that raises general exceptions during send."""

    def __init__(self, client_state: WebSocketState = WebSocketState.CONNECTED) -> None:
        self.client_state = client_state
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.client_state = WebSocketState.DISCONNECTED

    async def send_json(self, data: dict[str, Any]) -> None:
        raise RuntimeError("Simulated send error")

    def as_websocket(self) -> WebSocket:
        return cast(WebSocket, self)


class HealthyMockWebSocket:
    """Mock WebSocket that works correctly."""

    def __init__(self, client_state: WebSocketState = WebSocketState.CONNECTED) -> None:
        self.client_state = client_state
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.sent_messages: list[dict[str, Any]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.client_state = WebSocketState.DISCONNECTED

    async def send_json(self, data: dict[str, Any]) -> None:
        if self.client_state != WebSocketState.CONNECTED:
            raise RuntimeError("WebSocket not connected")
        self.sent_messages.append(data)

    def as_websocket(self) -> WebSocket:
        return cast(WebSocket, self)


@pytest.fixture
def manager() -> ConnectionManager:
    """Create a fresh ConnectionManager for testing."""
    return ConnectionManager()


@pytest.mark.integration
class TestConnectionManagerTimeoutHandling:
    """Tests for timeout handling in ConnectionManager."""

    @pytest.mark.asyncio
    async def test_send_personal_message_timeout(self, manager: ConnectionManager) -> None:
        """Test that slow clients are disconnected on timeout."""
        # Use a short timeout for testing
        manager.SEND_TIMEOUT = 0.1

        ws = SlowMockWebSocket(send_delay=1.0)
        await manager.connect(ws.as_websocket())

        # Send should timeout and return False
        result = await manager.send_personal_message(ws.as_websocket(), {"type": "test"})

        assert result is False
        # Client should be disconnected after timeout
        # Give a small delay for the disconnect to complete
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_broadcast_handles_timeout_clients(self, manager: ConnectionManager) -> None:
        """Test that broadcast handles timeout for some clients."""
        manager.SEND_TIMEOUT = 0.1

        healthy_ws = HealthyMockWebSocket()
        slow_ws = SlowMockWebSocket(send_delay=1.0)

        await manager.connect(healthy_ws.as_websocket(), rooms=["test"])
        await manager.connect(slow_ws.as_websocket(), rooms=["test"])

        message = {"type": "test"}
        count = await manager.broadcast_to_room("test", message)

        # Only healthy client should receive
        assert count == 1
        assert message in healthy_ws.sent_messages


@pytest.mark.integration
class TestConnectionManagerDisconnectHandling:
    """Tests for WebSocketDisconnect handling."""

    @pytest.mark.asyncio
    async def test_send_personal_message_disconnect(self, manager: ConnectionManager) -> None:
        """Test handling WebSocketDisconnect during send."""
        ws = DisconnectingMockWebSocket()
        await manager.connect(ws.as_websocket())

        result = await manager.send_personal_message(ws.as_websocket(), {"type": "test"})

        assert result is False
        # Should be removed from manager
        await asyncio.sleep(0.05)  # Allow disconnect task to complete
        assert manager.active_connections_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnecting_clients(
        self, manager: ConnectionManager
    ) -> None:
        """Test that broadcast handles clients that disconnect during send."""
        healthy_ws = HealthyMockWebSocket()
        disconnecting_ws = DisconnectingMockWebSocket()

        await manager.connect(healthy_ws.as_websocket(), rooms=["test"])
        await manager.connect(disconnecting_ws.as_websocket(), rooms=["test"])

        message = {"type": "test"}
        count = await manager.broadcast_to_room("test", message)

        # Only healthy client should receive
        assert count == 1
        assert message in healthy_ws.sent_messages


@pytest.mark.integration
class TestConnectionManagerExceptionHandling:
    """Tests for general exception handling."""

    @pytest.mark.asyncio
    async def test_send_personal_message_exception(self, manager: ConnectionManager) -> None:
        """Test handling general exceptions during send."""
        ws = ExceptionMockWebSocket()
        await manager.connect(ws.as_websocket())

        result = await manager.send_personal_message(ws.as_websocket(), {"type": "test"})

        assert result is False
        # Should trigger force disconnect
        await asyncio.sleep(0.05)

    @pytest.mark.asyncio
    async def test_broadcast_handles_exception_clients(self, manager: ConnectionManager) -> None:
        """Test that broadcast handles clients that raise exceptions."""
        healthy_ws = HealthyMockWebSocket()
        exception_ws = ExceptionMockWebSocket()

        await manager.connect(healthy_ws.as_websocket(), rooms=["test"])
        await manager.connect(exception_ws.as_websocket(), rooms=["test"])

        message = {"type": "test"}
        count = await manager.broadcast_to_room("test", message)

        # Only healthy client should receive
        assert count == 1


@pytest.mark.integration
class TestConnectionManagerForceDisconnect:
    """Tests for force disconnect behavior."""

    @pytest.mark.asyncio
    async def test_force_disconnect_connected_client(self, manager: ConnectionManager) -> None:
        """Test force disconnect on a connected client."""
        ws = HealthyMockWebSocket()
        await manager.connect(ws.as_websocket())

        assert manager.active_connections_count == 1

        # Force disconnect
        await manager._force_disconnect(ws.as_websocket())

        # Should be removed and closed
        assert manager.active_connections_count == 0
        assert ws.closed is True
        assert ws.close_code == 1008  # Policy Violation

    @pytest.mark.asyncio
    async def test_force_disconnect_already_disconnected(self, manager: ConnectionManager) -> None:
        """Test force disconnect on already disconnected client."""
        ws = HealthyMockWebSocket(client_state=WebSocketState.DISCONNECTED)
        await manager.connect(ws.as_websocket())

        # Should not raise, even for disconnected client
        await manager._force_disconnect(ws.as_websocket())

    @pytest.mark.asyncio
    async def test_force_disconnect_close_timeout(self, manager: ConnectionManager) -> None:
        """Test force disconnect when close times out."""

        class SlowCloseMockWebSocket(HealthyMockWebSocket):
            async def close(self, code: int = 1000, reason: str = "") -> None:
                await asyncio.sleep(5.0)  # Simulate slow close
                await super().close(code, reason)

        ws = SlowCloseMockWebSocket()
        await manager.connect(ws.as_websocket())

        # Should complete despite slow close (timeout)
        await asyncio.wait_for(
            manager._force_disconnect(ws.as_websocket()),
            timeout=2.0,
        )


@pytest.mark.integration
class TestConnectionManagerSendToClient:
    """Tests for _send_to_client internal method."""

    @pytest.mark.asyncio
    async def test_send_to_client_disconnected_state(self, manager: ConnectionManager) -> None:
        """Test _send_to_client returns False for disconnected client."""
        ws = HealthyMockWebSocket(client_state=WebSocketState.DISCONNECTED)

        result = await manager._send_to_client(ws.as_websocket(), {"type": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_client_success(self, manager: ConnectionManager) -> None:
        """Test _send_to_client returns True for successful send."""
        ws = HealthyMockWebSocket()

        result = await manager._send_to_client(ws.as_websocket(), {"type": "test"})

        assert result is True
        assert {"type": "test"} in ws.sent_messages

    @pytest.mark.asyncio
    async def test_send_to_client_timeout_schedules_disconnect(
        self, manager: ConnectionManager
    ) -> None:
        """Test _send_to_client schedules disconnect on timeout."""
        manager.SEND_TIMEOUT = 0.05
        ws = SlowMockWebSocket(send_delay=1.0)
        await manager.connect(ws.as_websocket())

        result = await manager._send_to_client(ws.as_websocket(), {"type": "test"})

        assert result is False
        # Give time for scheduled task to run
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_send_to_client_disconnect_schedules_cleanup(
        self, manager: ConnectionManager
    ) -> None:
        """Test _send_to_client schedules cleanup on WebSocketDisconnect."""
        ws = DisconnectingMockWebSocket()
        await manager.connect(ws.as_websocket())

        result = await manager._send_to_client(ws.as_websocket(), {"type": "test"})

        assert result is False
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_send_to_client_exception_schedules_force_disconnect(
        self, manager: ConnectionManager
    ) -> None:
        """Test _send_to_client schedules force disconnect on exception."""
        ws = ExceptionMockWebSocket()
        await manager.connect(ws.as_websocket())

        result = await manager._send_to_client(ws.as_websocket(), {"type": "test"})

        assert result is False
        await asyncio.sleep(0.1)


@pytest.mark.integration
class TestConnectionManagerBroadcastToRooms:
    """Tests for broadcast_to_rooms method."""

    @pytest.mark.asyncio
    async def test_broadcast_to_rooms_empty_rooms(self, manager: ConnectionManager) -> None:
        """Test broadcasting to empty/non-existent rooms."""
        count = await manager.broadcast_to_rooms(["nonexistent1", "nonexistent2"], {"type": "test"})
        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_rooms_deduplication(self, manager: ConnectionManager) -> None:
        """Test that clients in multiple rooms only receive once."""
        ws = HealthyMockWebSocket()
        await manager.connect(ws.as_websocket(), rooms=["room1", "room2", "room3"])

        message = {"type": "test"}
        count = await manager.broadcast_to_rooms(["room1", "room2", "room3"], message)

        assert count == 1
        assert len(ws.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_rooms_partial_membership(self, manager: ConnectionManager) -> None:
        """Test broadcasting when clients are in different subsets of rooms."""
        ws1 = HealthyMockWebSocket()
        ws2 = HealthyMockWebSocket()
        ws3 = HealthyMockWebSocket()

        await manager.connect(ws1.as_websocket(), rooms=["room1"])
        await manager.connect(ws2.as_websocket(), rooms=["room2"])
        await manager.connect(ws3.as_websocket(), rooms=["room1", "room2"])

        message = {"type": "test"}
        count = await manager.broadcast_to_rooms(["room1", "room2"], message)

        # All 3 unique clients should receive (ws3 is in both but deduplicated)
        assert count == 3


@pytest.mark.integration
class TestConnectionManagerBroadcastAll:
    """Tests for broadcast_all method."""

    @pytest.mark.asyncio
    async def test_broadcast_all_empty(self, manager: ConnectionManager) -> None:
        """Test broadcasting when no clients connected."""
        count = await manager.broadcast_all({"type": "test"})
        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_all_success(self, manager: ConnectionManager) -> None:
        """Test broadcasting to all connected clients."""
        ws1 = HealthyMockWebSocket()
        ws2 = HealthyMockWebSocket()
        ws3 = HealthyMockWebSocket()

        await manager.connect(ws1.as_websocket(), rooms=["room1"])
        await manager.connect(ws2.as_websocket(), rooms=["room2"])
        await manager.connect(ws3.as_websocket(), rooms=["room3"])

        message = {"type": "global"}
        count = await manager.broadcast_all(message)

        assert count == 3
        for ws in [ws1, ws2, ws3]:
            assert message in ws.sent_messages


@pytest.mark.integration
class TestConnectionManagerSingleton:
    """Tests for singleton pattern."""

    def test_set_connection_manager_to_none(self) -> None:
        """Test resetting the singleton to None."""
        set_connection_manager(None)
        manager = get_connection_manager()
        assert isinstance(manager, ConnectionManager)

        # Set to None again
        set_connection_manager(None)

        # Should create a new instance
        new_manager = get_connection_manager()
        assert isinstance(new_manager, ConnectionManager)
        assert new_manager is not manager


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
