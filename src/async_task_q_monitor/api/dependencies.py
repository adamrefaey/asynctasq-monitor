"""Dependency providers for the API package.

This module follows FastAPI 0.122+ best practices:
- Use Annotated[] for dependency declarations (PEP 593)
- Use async context managers for resources needing cleanup
- Provide typed dependencies for settings, services, and pagination
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Query, Request

from async_task_q_monitor.config import Settings, get_settings
from async_task_q_monitor.services.task_service import TaskService
from async_task_q_monitor.services.worker_service import WorkerService

# ---------------------------------------------------------------------------
# Settings Dependency
# ---------------------------------------------------------------------------


def get_settings_dependency() -> Settings:
    """Get application settings.

    Uses cached get_settings() from config module.
    """
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]


# ---------------------------------------------------------------------------
# Task Service Dependency
# ---------------------------------------------------------------------------


@lru_cache
def _get_task_service_singleton() -> TaskService:
    """Internal singleton factory for TaskService.

    Using lru_cache for lightweight singleton pattern.
    """
    return TaskService()


def get_task_service() -> TaskService:
    """Return a TaskService for dependency injection.

    For production, this uses a singleton pattern.
    For testing, this dependency can be overridden in app.dependency_overrides.
    """
    return _get_task_service_singleton()


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


# ---------------------------------------------------------------------------
# Worker Service Dependency
# ---------------------------------------------------------------------------


@lru_cache
def _get_worker_service_singleton() -> WorkerService:
    """Internal singleton factory for WorkerService.

    Using lru_cache for lightweight singleton pattern.
    """
    return WorkerService()


def get_worker_service() -> WorkerService:
    """Return a WorkerService for dependency injection.

    For production, this uses a singleton pattern.
    For testing, this dependency can be overridden in app.dependency_overrides.
    """
    return _get_worker_service_singleton()


WorkerServiceDep = Annotated[WorkerService, Depends(get_worker_service)]


# ---------------------------------------------------------------------------
# Request Context Dependency
# ---------------------------------------------------------------------------


async def get_request_state(request: Request) -> dict:
    """Access app.state as a dependency for request context.

    This can be used to access shared state initialized during lifespan.

    Args:
        request: The incoming FastAPI request.

    Returns:
        Dictionary of app state items.
    """
    return dict(request.app.state._state)


RequestStateDep = Annotated[dict, Depends(get_request_state)]


# ---------------------------------------------------------------------------
# Pagination Parameters
# ---------------------------------------------------------------------------


def pagination_params(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
            description="Maximum number of items to return per page",
        ),
    ] = 50,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of items to skip for pagination",
        ),
    ] = 0,
) -> tuple[int, int]:
    """Common pagination parameters for list endpoints.

    Returns:
        Tuple of (limit, offset) values.
    """
    return (limit, offset)


PaginationDep = Annotated[tuple[int, int], Depends(pagination_params)]


# ---------------------------------------------------------------------------
# Async Resource Dependencies (for cleanup patterns)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def get_scoped_task_service() -> AsyncIterator[TaskService]:
    """Async context manager for TaskService with cleanup.

    Use this pattern when TaskService needs initialization/cleanup per request.
    Currently uses singleton, but demonstrates the pattern.

    Example:
        @app.get("/tasks")
        async def list_tasks(
            service: Annotated[TaskService, Depends(get_scoped_task_service)]
        ):
            ...
    """
    service = _get_task_service_singleton()
    try:
        yield service
    finally:
        # Add cleanup logic here if needed (e.g., close connections)
        pass


# ---------------------------------------------------------------------------
# Dependency Factories (for parameterized dependencies)
# ---------------------------------------------------------------------------


def create_pagination_dep(
    default_limit: int = 50,
    max_limit: int = 500,
) -> Callable[..., tuple[int, int]]:
    """Factory function to create custom pagination dependencies.

    This pattern allows creating specialized pagination for different endpoints.

    Args:
        default_limit: Default number of items per page.
        max_limit: Maximum allowed items per page.

    Returns:
        A dependency function with the specified defaults.

    Example:
        SmallPageDep = Annotated[tuple[int, int], Depends(create_pagination_dep(10, 100))]
    """

    def _pagination(
        limit: Annotated[int, Query(ge=1, le=max_limit)] = default_limit,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> tuple[int, int]:
        return (limit, offset)

    return _pagination


# Pre-configured pagination for small pages (useful for modals, dropdowns)
SmallPaginationDep = Annotated[tuple[int, int], Depends(create_pagination_dep(10, 100))]
