"""WebSocket infrastructure for real-time monitoring updates."""

from asynctasq_monitor.websocket.broadcaster import (
    EventBroadcaster,
    get_event_broadcaster,
    set_event_broadcaster,
)
from asynctasq_monitor.websocket.events import (
    MetricsEvent,
    QueueEvent,
    TaskEvent,
    WebSocketEvent,
    WebSocketEventType,
    WorkerEvent,
)
from asynctasq_monitor.websocket.manager import (
    ConnectionManager,
    get_connection_manager,
    set_connection_manager,
)
from asynctasq_monitor.websocket.redis_pubsub import (
    RedisPubSubBroker,
    get_redis_broker,
    init_redis_broker,
    shutdown_redis_broker,
)

__all__ = [
    # Manager
    "ConnectionManager",
    "get_connection_manager",
    "set_connection_manager",
    # Broadcaster
    "EventBroadcaster",
    "get_event_broadcaster",
    "set_event_broadcaster",
    # Events
    "WebSocketEvent",
    "WebSocketEventType",
    "TaskEvent",
    "WorkerEvent",
    "QueueEvent",
    "MetricsEvent",
    # Redis Pub/Sub
    "RedisPubSubBroker",
    "get_redis_broker",
    "init_redis_broker",
    "shutdown_redis_broker",
]
