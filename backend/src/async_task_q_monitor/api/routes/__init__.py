"""API route collection for async_task_q_monitor."""

from . import dashboard, metrics, queues, tasks, websocket, workers

__all__ = ["dashboard", "metrics", "queues", "tasks", "websocket", "workers"]
