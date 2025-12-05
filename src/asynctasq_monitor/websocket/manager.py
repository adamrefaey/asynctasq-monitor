"""WebSocket connection manager with rooms pattern.

This module implements a WebSocket connection manager following FastAPI best practices:
- Room-based broadcasting for targeted updates
- Thread-safe connection tracking with asyncio locks
- Graceful disconnection handling
- Backpressure handling for slow clients
- JSON serialization with Pydantic v2
"""

import asyncio
from collections import defaultdict
import logging
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterable


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections with room-based broadcasting.

    This manager implements the rooms pattern for efficient message routing:
    - `global` - Dashboard overview, receives all high-level updates
    - `tasks` - Task list updates (new, completed, failed)
    - `task:{id}` - Specific task updates
    - `workers` - Worker list updates
    - `worker:{id}` - Specific worker updates
    - `queues` - Queue list updates
    - `queue:{name}` - Specific queue updates

    Thread Safety:
        All operations that modify connection state use asyncio.Lock to ensure
        thread safety in concurrent async contexts.

    Backpressure Handling:
        Messages are sent with a timeout. Slow clients that don't receive
        within the timeout are disconnected to prevent memory buildup.
    """

    # Timeout for sending messages to clients (seconds)
    SEND_TIMEOUT: float = 5.0

    # Maximum message queue size per connection before backpressure kicks in
    MAX_QUEUE_SIZE: int = 100

    def __init__(self) -> None:
        """Initialize the connection manager with empty room mappings."""
        # Maps room name to set of connected WebSocket clients
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

        # Maps WebSocket to the rooms it has subscribed to
        self._subscriptions: dict[WebSocket, set[str]] = defaultdict(set)

        # Lock for thread-safe operations
        self._lock: asyncio.Lock = asyncio.Lock()

        logger.debug("ConnectionManager initialized")

    @property
    def active_connections_count(self) -> int:
        """Return total number of unique active connections."""
        return len(self._subscriptions)

    @property
    def room_counts(self) -> dict[str, int]:
        """Return a mapping of room names to connection counts."""
        return {room: len(clients) for room, clients in self._rooms.items() if clients}

    async def connect(self, websocket: WebSocket, rooms: "Iterable[str] | None" = None) -> None:
        """Accept a WebSocket connection and subscribe to specified rooms.

        Args:
            websocket: The WebSocket connection to accept
            rooms: Iterable of room names to subscribe to. Defaults to ["global"]
        """
        await websocket.accept()

        rooms_to_join = set(rooms) if rooms else {"global"}

        async with self._lock:
            for room in rooms_to_join:
                self._rooms[room].add(websocket)
                self._subscriptions[websocket].add(room)

        logger.info(
            "WebSocket connected and subscribed to rooms: %s (total: %d)",
            rooms_to_join,
            self.active_connections_count,
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from all rooms and clean up.

        Args:
            websocket: The WebSocket connection to remove
        """
        async with self._lock:
            # Get all rooms this websocket was subscribed to
            rooms = self._subscriptions.pop(websocket, set())

            # Remove from each room
            for room in rooms:
                self._rooms[room].discard(websocket)
                # Clean up empty rooms (except 'global' which we always keep)
                if not self._rooms[room] and room != "global":
                    del self._rooms[room]

        logger.info(
            "WebSocket disconnected from rooms: %s (remaining: %d)",
            rooms,
            self.active_connections_count,
        )

    async def subscribe(self, websocket: WebSocket, room: str) -> None:
        """Subscribe a WebSocket to an additional room.

        Args:
            websocket: The WebSocket connection
            room: The room name to subscribe to
        """
        async with self._lock:
            self._rooms[room].add(websocket)
            self._subscriptions[websocket].add(room)

        logger.debug("WebSocket subscribed to room: %s", room)

    async def unsubscribe(self, websocket: WebSocket, room: str) -> None:
        """Unsubscribe a WebSocket from a room.

        Args:
            websocket: The WebSocket connection
            room: The room name to unsubscribe from
        """
        async with self._lock:
            self._rooms[room].discard(websocket)
            self._subscriptions[websocket].discard(room)

            # Clean up empty rooms
            if not self._rooms[room] and room != "global":
                del self._rooms[room]

        logger.debug("WebSocket unsubscribed from room: %s", room)

    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: dict[str, Any] | BaseModel,
    ) -> bool:
        """Send a message directly to a specific WebSocket.

        Args:
            websocket: The target WebSocket connection
            message: The message to send (dict or Pydantic model)

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # Check if connection is still open
            if websocket.client_state != WebSocketState.CONNECTED:
                return False

            # Serialize Pydantic models to JSON-compatible dict
            if isinstance(message, BaseModel):
                data = message.model_dump(mode="json")
            else:
                data = message

            # Send with timeout to handle slow clients
            await asyncio.wait_for(
                websocket.send_json(data),
                timeout=self.SEND_TIMEOUT,
            )
            return True

        except TimeoutError:
            logger.warning("Send timeout, disconnecting slow client")
            await self._force_disconnect(websocket)
            return False

        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected during send")
            await self.disconnect(websocket)
            return False

        except Exception:
            logger.exception("Error sending message to WebSocket")
            await self._force_disconnect(websocket)
            return False

    async def broadcast_to_room(
        self,
        room: str,
        message: dict[str, Any] | BaseModel,
    ) -> int:
        """Broadcast a message to all connections in a room.

        Args:
            room: The room name to broadcast to
            message: The message to send (dict or Pydantic model)

        Returns:
            Number of connections that received the message
        """
        async with self._lock:
            clients = list(self._rooms.get(room, set()))

        if not clients:
            return 0

        # Serialize once for efficiency
        if isinstance(message, BaseModel):
            data = message.model_dump(mode="json")
        else:
            data = message

        # Send to all clients concurrently
        tasks = [self._send_to_client(ws, data) for ws in clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful sends
        success_count = sum(1 for r in results if r is True)
        logger.debug(
            "Broadcast to room '%s': %d/%d clients received",
            room,
            success_count,
            len(clients),
        )
        return success_count

    async def broadcast_to_rooms(
        self,
        rooms: "Iterable[str]",
        message: dict[str, Any] | BaseModel,
    ) -> int:
        """Broadcast a message to multiple rooms (deduplicating recipients).

        Args:
            rooms: Iterable of room names to broadcast to
            message: The message to send (dict or Pydantic model)

        Returns:
            Number of unique connections that received the message
        """
        # Collect unique clients across all rooms
        unique_clients: set[WebSocket] = set()
        async with self._lock:
            for room in rooms:
                unique_clients.update(self._rooms.get(room, set()))

        if not unique_clients:
            return 0

        # Serialize once for efficiency
        if isinstance(message, BaseModel):
            data = message.model_dump(mode="json")
        else:
            data = message

        # Send to all unique clients concurrently
        tasks = [self._send_to_client(ws, data) for ws in unique_clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        logger.debug(
            "Broadcast to rooms %s: %d/%d unique clients received",
            list(rooms),
            success_count,
            len(unique_clients),
        )
        return success_count

    async def broadcast_all(
        self,
        message: dict[str, Any] | BaseModel,
    ) -> int:
        """Broadcast a message to all connected clients.

        Args:
            message: The message to send (dict or Pydantic model)

        Returns:
            Number of connections that received the message
        """
        async with self._lock:
            all_clients = list(self._subscriptions.keys())

        if not all_clients:
            return 0

        # Serialize once for efficiency
        if isinstance(message, BaseModel):
            data = message.model_dump(mode="json")
        else:
            data = message

        tasks = [self._send_to_client(ws, data) for ws in all_clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        logger.debug("Broadcast to all: %d/%d clients received", success_count, len(all_clients))
        return success_count

    async def _send_to_client(self, websocket: WebSocket, data: dict[str, Any]) -> bool:
        """Internal method to send data to a single client with error handling.

        Args:
            websocket: Target WebSocket
            data: Pre-serialized data to send

        Returns:
            True if successful, False otherwise
        """
        try:
            if websocket.client_state != WebSocketState.CONNECTED:
                return False

            await asyncio.wait_for(
                websocket.send_json(data),
                timeout=self.SEND_TIMEOUT,
            )
            return True

        except TimeoutError:
            logger.warning("Send timeout to client, scheduling disconnect")
            # Schedule disconnect without blocking
            asyncio.create_task(self._force_disconnect(websocket))
            return False

        except WebSocketDisconnect:
            asyncio.create_task(self.disconnect(websocket))
            return False

        except Exception:
            logger.exception("Error sending to client")
            asyncio.create_task(self._force_disconnect(websocket))
            return False

    async def _force_disconnect(self, websocket: WebSocket) -> None:
        """Force disconnect a WebSocket, attempting graceful close first.

        Args:
            websocket: The WebSocket to disconnect
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await asyncio.wait_for(
                    websocket.close(code=1008, reason="Connection timeout"),
                    timeout=1.0,
                )
        except Exception:
            pass  # Best effort close
        finally:
            await self.disconnect(websocket)

    def get_rooms_for_connection(self, websocket: WebSocket) -> set[str]:
        """Get all rooms a WebSocket is subscribed to.

        Args:
            websocket: The WebSocket connection

        Returns:
            Set of room names
        """
        return self._subscriptions.get(websocket, set()).copy()

    def get_connections_in_room(self, room: str) -> int:
        """Get the number of connections in a specific room.

        Args:
            room: The room name

        Returns:
            Number of connections
        """
        return len(self._rooms.get(room, set()))


# Global singleton instance for use across the application
_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global ConnectionManager singleton.

    This pattern allows for easy testing by replacing the global instance.

    Returns:
        The global ConnectionManager instance
    """
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


def set_connection_manager(manager: ConnectionManager | None) -> None:
    """Set the global ConnectionManager instance (for testing).

    Args:
        manager: The ConnectionManager to use, or None to reset
    """
    global _manager
    _manager = manager
