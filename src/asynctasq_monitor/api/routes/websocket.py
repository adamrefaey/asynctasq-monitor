"""WebSocket endpoints for real-time monitoring updates.

This module implements WebSocket endpoints following FastAPI best practices:
- Room-based subscriptions for targeted updates
- Dependency injection for connection management
- Proper error handling with WebSocketDisconnect
- Query parameter validation with Annotated types
- Graceful connection lifecycle management
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from asynctasq_monitor.websocket.manager import (
    ConnectionManager,
    get_connection_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_manager() -> ConnectionManager:
    """Dependency that provides the ConnectionManager singleton.

    This wrapper allows for easy testing by mocking the dependency.
    """
    return get_connection_manager()


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    rooms: Annotated[
        list[str] | None,
        Query(
            description="Room names to subscribe to. Defaults to ['global']. "
            "Valid rooms: global, tasks, task:{id}, workers, worker:{id}, queues, queue:{name}",
        ),
    ] = None,
    manager: Annotated[ConnectionManager, Depends(_get_manager)] = None,  # type: ignore[assignment]
) -> None:
    """WebSocket endpoint for real-time monitoring updates.

    Clients can subscribe to one or more rooms to receive targeted updates:

    **Room Types:**
    - `global` - Dashboard overview, receives all high-level updates
    - `tasks` - Task list updates (new, completed, failed)
    - `task:{id}` - Specific task updates (e.g., `task:550e8400-...`)
    - `workers` - Worker list updates
    - `worker:{id}` - Specific worker updates (e.g., `worker:worker-1`)
    - `queues` - Queue list updates
    - `queue:{name}` - Specific queue updates (e.g., `queue:emails`)

    **Example Connection URLs:**
    - `ws://localhost:8000/ws` - Subscribe to `global` room only
    - `ws://localhost:8000/ws?rooms=tasks&rooms=workers` - Subscribe to multiple rooms
    - `ws://localhost:8000/ws?rooms=task:abc123` - Subscribe to specific task

    **Message Format:**
    All messages are JSON objects with at minimum a `type` field:
    ```json
    {
        "type": "task_completed",
        "task_id": "abc123",
        "timestamp": "2025-12-02T10:00:00Z",
        ...
    }
    ```

    **Client Commands:**
    Clients can send JSON commands to manage subscriptions:
    - `{"action": "subscribe", "room": "task:abc123"}` - Subscribe to a room
    - `{"action": "unsubscribe", "room": "task:abc123"}` - Unsubscribe from a room
    - `{"action": "ping"}` - Heartbeat (server responds with pong)
    """
    # Connect and subscribe to initial rooms
    initial_rooms = rooms if rooms else ["global"]
    await manager.connect(websocket, rooms=initial_rooms)

    try:
        # Message handling loop
        while True:
            # Receive and parse client messages
            try:
                data = await websocket.receive_json()
            except ValueError:
                # Invalid JSON, send error and continue
                await manager.send_personal_message(
                    websocket,
                    {"type": "error", "message": "Invalid JSON"},
                )
                continue

            # Handle client commands
            action = data.get("action")

            if action == "ping":
                await manager.send_personal_message(
                    websocket,
                    {"type": "pong"},
                )

            elif action == "subscribe":
                room = data.get("room")
                if room and isinstance(room, str):
                    await manager.subscribe(websocket, room)
                    await manager.send_personal_message(
                        websocket,
                        {"type": "subscribed", "room": room},
                    )
                else:
                    await manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Invalid room name"},
                    )

            elif action == "unsubscribe":
                room = data.get("room")
                if room and isinstance(room, str):
                    await manager.unsubscribe(websocket, room)
                    await manager.send_personal_message(
                        websocket,
                        {"type": "unsubscribed", "room": room},
                    )
                else:
                    await manager.send_personal_message(
                        websocket,
                        {"type": "error", "message": "Invalid room name"},
                    )

            elif action == "list_rooms":
                current_rooms = manager.get_rooms_for_connection(websocket)
                await manager.send_personal_message(
                    websocket,
                    {"type": "rooms", "rooms": list(current_rooms)},
                )

            else:
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                        "valid_actions": ["ping", "subscribe", "unsubscribe", "list_rooms"],
                    },
                )

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception:
        logger.exception("Error in WebSocket handler")
    finally:
        # Clean up connection on any exit
        await manager.disconnect(websocket)


@router.get("/stats")
async def websocket_stats(
    manager: Annotated[ConnectionManager, Depends(_get_manager)],
) -> dict:
    """Get WebSocket connection statistics.

    Returns:
        Dictionary with connection counts per room and total connections.
    """
    return {
        "total_connections": manager.active_connections_count,
        "rooms": manager.room_counts,
    }
