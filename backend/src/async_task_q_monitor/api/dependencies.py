"""Dependency providers for the API package."""

from functools import lru_cache

from async_task_q_monitor.services.task_service import TaskService


@lru_cache
def get_task_service() -> TaskService:
    """Return a singleton TaskService for dependency injection.

    Using `lru_cache` is a pragmatic choice for a lightweight singleton.
    For stricter test control, create the service on app startup and store
    it in `app.state`, then retrieve it via a dependency that accesses
    `request.app.state`.
    """
    return TaskService()
