"""Pytest configuration and shared fixtures.

This module follows pytest best practices:
- Use pytest-asyncio with strict mode for async tests
- Use factory fixtures for customizable test data
- Use dependency_overrides pattern for FastAPI testing
- Provide both sync and async client fixtures
"""

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest
from starlette.testclient import TestClient

from async_task_q_monitor.api.dependencies import get_task_service
from async_task_q_monitor.api.main import create_monitoring_app
from async_task_q_monitor.config import Settings, get_settings
from async_task_q_monitor.models.task import Task, TaskFilters, TaskStatus

# ============================================================================
# Mock Service
# ============================================================================


class MockTaskService:
    """Mock TaskService for testing without actual queue backend."""

    def __init__(self, *, tasks: list[Task] | None = None) -> None:
        """Initialize with optional list of tasks."""
        self._tasks = list(tasks) if tasks else []

    async def get_tasks(
        self,
        filters: TaskFilters,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Return filtered and paginated tasks."""
        items = self._tasks

        if filters.status is not None:
            items = [t for t in items if t.status == filters.status]
        if filters.queue is not None:
            items = [t for t in items if t.queue == filters.queue]
        if filters.worker_id is not None:
            items = [t for t in items if t.worker_id == filters.worker_id]
        if filters.search is not None:
            search_lower = filters.search.lower()
            items = [
                t for t in items if search_lower in t.name.lower() or search_lower in t.id.lower()
            ]
        if filters.tags is not None:
            items = [t for t in items if any(tag in t.tags for tag in filters.tags)]

        total = len(items)
        return items[offset : offset + limit], total

    async def get_task_by_id(self, task_id: str) -> Task | None:
        """Return a task by ID or None if not found."""
        for t in self._tasks:
            if t.id == task_id:
                return t
        return None

    async def retry_task(self, task_id: str) -> bool:
        """Attempt to retry a failed task."""
        task = await self.get_task_by_id(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        # In real implementation this would re-enqueue
        return True

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        for i, t in enumerate(self._tasks):
            if t.id == task_id:
                del self._tasks[i]
                return True
        return False

    def add_task(self, task: Task) -> None:
        """Add a task to the mock store (for test setup)."""
        self._tasks.append(task)

    def clear(self) -> None:
        """Clear all tasks (for test cleanup)."""
        self._tasks.clear()


# ============================================================================
# Factory Fixtures
# ============================================================================


@pytest.fixture
def task_factory() -> Callable[..., Task]:
    """Factory fixture for creating Task instances with customizable fields.

    Example:
        def test_something(task_factory):
            task = task_factory(name="my-task", status=TaskStatus.FAILED)
            assert task.status == TaskStatus.FAILED
    """

    def _create_task(
        *,
        id: str | None = None,
        name: str = "test-task",
        queue: str = "default",
        status: TaskStatus = TaskStatus.PENDING,
        enqueued_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_ms: int | None = None,
        worker_id: str | None = None,
        attempt: int = 1,
        max_retries: int = 3,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        result: Any | None = None,
        exception: str | None = None,
        traceback: str | None = None,
        priority: int = 0,
        timeout_seconds: int | None = None,
        tags: list[str] | None = None,
    ) -> Task:
        return Task(
            id=id or str(uuid4()),
            name=name,
            queue=queue,
            status=status,
            enqueued_at=enqueued_at or datetime.now(UTC),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            worker_id=worker_id,
            attempt=attempt,
            max_retries=max_retries,
            args=args or [],
            kwargs=kwargs or {},
            result=result,
            exception=exception,
            traceback=traceback,
            priority=priority,
            timeout_seconds=timeout_seconds,
            tags=tags or [],
        )

    return _create_task


@pytest.fixture
def sample_tasks(task_factory: Callable[..., Task]) -> list[Task]:
    """Generate a set of sample tasks for testing."""
    now = datetime.now(UTC)
    return [
        task_factory(
            id="t1",
            name="send-email",
            status=TaskStatus.PENDING,
            queue="emails",
            enqueued_at=now,
            priority=1,
            tags=["transactional"],
        ),
        task_factory(
            id="t2",
            name="process-payment",
            status=TaskStatus.FAILED,
            queue="payments",
            enqueued_at=now - timedelta(minutes=5),
            started_at=now - timedelta(minutes=4),
            completed_at=now - timedelta(minutes=3),
            duration_ms=60000,
            worker_id="worker-1",
            attempt=3,
            exception="PaymentGatewayError: Connection timeout",
            traceback="Traceback (most recent call last):\n  ...",
            tags=["critical"],
        ),
        task_factory(
            id="t3",
            name="generate-report",
            status=TaskStatus.COMPLETED,
            queue="reports",
            enqueued_at=now - timedelta(hours=1),
            started_at=now - timedelta(minutes=50),
            completed_at=now - timedelta(minutes=45),
            duration_ms=300000,
            worker_id="worker-2",
            result={"report_url": "https://example.com/report.pdf"},
        ),
        task_factory(
            id="t4",
            name="send-notification",
            status=TaskStatus.RUNNING,
            queue="notifications",
            enqueued_at=now - timedelta(seconds=30),
            started_at=now - timedelta(seconds=10),
            worker_id="worker-1",
        ),
    ]


# ============================================================================
# Service Fixtures
# ============================================================================


@pytest.fixture
def mock_task_service(sample_tasks: list[Task]) -> MockTaskService:
    """Create a MockTaskService populated with sample tasks."""
    return MockTaskService(tasks=sample_tasks)


@pytest.fixture
def empty_mock_task_service() -> MockTaskService:
    """Create an empty MockTaskService for testing empty states."""
    return MockTaskService()


@pytest.fixture
def test_settings() -> Settings:
    """Create test-specific settings."""
    return Settings(
        debug=True,
        host="127.0.0.1",
        port=8080,
        cors_origins=["http://localhost:3000"],
        enable_auth=False,
        secret_key="test-secret-key-for-testing-only",
        polling_interval_seconds=1,
        log_level="DEBUG",
    )


# ============================================================================
# App & Client Fixtures
# ============================================================================


@pytest.fixture
def app(mock_task_service: MockTaskService, test_settings: Settings) -> FastAPI:
    """Create a FastAPI app with mocked dependencies."""
    app: FastAPI = create_monitoring_app()

    async def _override_get_task_service() -> MockTaskService:
        return mock_task_service

    def _override_get_settings() -> Settings:
        return test_settings

    app.dependency_overrides[get_task_service] = _override_get_task_service
    app.dependency_overrides[get_settings] = _override_get_settings

    return app


@pytest.fixture
def sync_client(app: FastAPI) -> Iterator[TestClient]:
    """Synchronous test client for non-async tests.

    Example:
        def test_health(sync_client):
            response = sync_client.get("/api/")
            assert response.status_code == 200
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async test client for async tests.

    Example:
        async def test_health(async_client):
            response = await async_client.get("/api/")
            assert response.status_code == 200
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and helpers."""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )

    # Load test helpers module
    import importlib.util
    from pathlib import Path

    helpers_path = Path(__file__).parent / "_helpers.py"
    if helpers_path.exists():
        spec = importlib.util.spec_from_file_location("test_helpers", helpers_path)
        if spec is not None and spec.loader is not None:
            _helpers = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_helpers)  # type: ignore[arg-type]

            # Assign helpers to pytest namespace
            if not hasattr(pytest, "helpers"):
                pytest.helpers = _helpers  # type: ignore[attr-defined]


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Modify test collection to auto-mark async tests."""
    import asyncio

    for item in items:
        # Auto-add asyncio marker to async test functions
        if isinstance(item, pytest.Function):
            if asyncio.iscoroutinefunction(item.obj):
                item.add_marker(pytest.mark.asyncio)
