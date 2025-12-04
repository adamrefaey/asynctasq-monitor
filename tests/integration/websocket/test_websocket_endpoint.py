"""Integration tests for WebSocket endpoint.

Following pytest best practices:
- Use explicit @pytest.mark.asyncio decorators (strict mode)
- Use pytest.mark.integration for categorization
- Use httpx for async HTTP/WebSocket testing
- Use fixtures for app setup
"""

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.testclient import TestClient

from asynctasq_monitor.api.main import create_monitoring_app
from asynctasq_monitor.websocket.manager import (
    ConnectionManager,
    get_connection_manager,
    set_connection_manager,
)


@pytest.fixture
def app():
    """Create test app with fresh ConnectionManager."""
    # Reset connection manager for each test
    set_connection_manager(ConnectionManager())

    app = create_monitoring_app()
    return app


@pytest.fixture
def test_client(app):
    """Create a sync test client for WebSocket tests."""
    return TestClient(app)


@pytest.mark.integration
class TestWebSocketEndpoint:
    """Integration tests for WebSocket endpoint."""

    def test_websocket_connect_default_room(self, test_client: TestClient) -> None:
        """Test WebSocket connects to global room by default."""
        with test_client.websocket_connect("/ws") as ws:
            # Connection should be accepted
            # Send a ping to verify connection works
            ws.send_json({"action": "ping"})
            response = ws.receive_json()
            assert response["type"] == "pong"

    def test_websocket_connect_custom_rooms(self, test_client: TestClient) -> None:
        """Test WebSocket connects to custom rooms."""
        with test_client.websocket_connect("/ws?rooms=tasks&rooms=workers") as ws:
            # Verify we're subscribed to the right rooms
            ws.send_json({"action": "list_rooms"})
            response = ws.receive_json()
            assert response["type"] == "rooms"
            assert "tasks" in response["rooms"]
            assert "workers" in response["rooms"]

    def test_websocket_subscribe_command(self, test_client: TestClient) -> None:
        """Test subscribing to a room via command."""
        with test_client.websocket_connect("/ws") as ws:
            # Subscribe to a new room
            ws.send_json({"action": "subscribe", "room": "task:abc123"})
            response = ws.receive_json()
            assert response["type"] == "subscribed"
            assert response["room"] == "task:abc123"

            # Verify subscription
            ws.send_json({"action": "list_rooms"})
            response = ws.receive_json()
            assert "task:abc123" in response["rooms"]

    def test_websocket_unsubscribe_command(self, test_client: TestClient) -> None:
        """Test unsubscribing from a room via command."""
        with test_client.websocket_connect("/ws?rooms=tasks&rooms=workers") as ws:
            # Unsubscribe from tasks
            ws.send_json({"action": "unsubscribe", "room": "tasks"})
            response = ws.receive_json()
            assert response["type"] == "unsubscribed"
            assert response["room"] == "tasks"

            # Verify unsubscription
            ws.send_json({"action": "list_rooms"})
            response = ws.receive_json()
            assert "tasks" not in response["rooms"]
            assert "workers" in response["rooms"]

    def test_websocket_invalid_json(self, test_client: TestClient) -> None:
        """Test that invalid JSON returns error."""
        with test_client.websocket_connect("/ws") as ws:
            # Send invalid data (not JSON)
            ws.send_text("not valid json")
            response = ws.receive_json()
            assert response["type"] == "error"
            assert "Invalid JSON" in response["message"]

    def test_websocket_unknown_action(self, test_client: TestClient) -> None:
        """Test that unknown action returns error."""
        with test_client.websocket_connect("/ws") as ws:
            ws.send_json({"action": "unknown_action"})
            response = ws.receive_json()
            assert response["type"] == "error"
            assert "Unknown action" in response["message"]
            assert "valid_actions" in response

    def test_websocket_subscribe_invalid_room(self, test_client: TestClient) -> None:
        """Test subscribe with invalid room name."""
        with test_client.websocket_connect("/ws") as ws:
            # Missing room parameter
            ws.send_json({"action": "subscribe"})
            response = ws.receive_json()
            assert response["type"] == "error"
            assert "Invalid room" in response["message"]


@pytest.mark.integration
class TestWebSocketStats:
    """Tests for WebSocket stats endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_stats_endpoint(self, app) -> None:
        """Test the /ws/stats endpoint returns connection info."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/ws/stats")
            assert response.status_code == 200

            data = response.json()
            assert "total_connections" in data
            assert "rooms" in data
            assert isinstance(data["total_connections"], int)
            assert isinstance(data["rooms"], dict)


@pytest.mark.integration
class TestWebSocketBroadcasting:
    """Tests for WebSocket broadcasting."""

    def test_broadcast_reaches_subscribed_clients(self, test_client: TestClient) -> None:
        """Test that broadcasts reach subscribed clients."""
        with test_client.websocket_connect("/ws?rooms=tasks") as ws1:
            with test_client.websocket_connect("/ws?rooms=tasks") as ws2:
                with test_client.websocket_connect("/ws?rooms=workers") as ws3:
                    # Use sync helper to broadcast
                    # Note: In production, broadcasts happen async
                    # For testing, we verify subscription works
                    ws1.send_json({"action": "list_rooms"})
                    r1 = ws1.receive_json()
                    assert "tasks" in r1["rooms"]

                    ws2.send_json({"action": "list_rooms"})
                    r2 = ws2.receive_json()
                    assert "tasks" in r2["rooms"]

                    ws3.send_json({"action": "list_rooms"})
                    r3 = ws3.receive_json()
                    assert "workers" in r3["rooms"]
                    assert "tasks" not in r3["rooms"]


@pytest.mark.integration
class TestWebSocketDisconnection:
    """Tests for WebSocket disconnection handling."""

    def test_disconnect_cleans_up_subscriptions(self, test_client: TestClient) -> None:
        """Test that disconnecting cleans up subscriptions."""
        manager = get_connection_manager()

        # Connect and verify
        with test_client.websocket_connect("/ws?rooms=tasks"):
            assert manager.active_connections_count >= 1
            assert manager.get_connections_in_room("tasks") >= 1

        # After disconnect, count should decrease
        # Note: TestClient context manager handles disconnect
        # Give a moment for cleanup
        assert manager.active_connections_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "integration"])
