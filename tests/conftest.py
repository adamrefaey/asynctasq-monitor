from datetime import UTC, datetime
from typing import Any, cast

from fastapi import FastAPI
import pytest

from async_task_q_monitor.api.dependencies import get_task_service
from async_task_q_monitor.api.main import create_monitoring_app
from async_task_q_monitor.models.task import Task, TaskFilters, TaskStatus


class MockTaskService:
    def __init__(self, *, tasks: list[Task] | None = None):
        self._tasks = tasks or []

    async def get_tasks(
        self, filters: TaskFilters, limit: int = 50, offset: int = 0
    ) -> tuple[list[Task], int]:
        items = self._tasks
        if filters.status is not None:
            items = [t for t in items if t.status == filters.status]
        if filters.queue is not None:
            items = [t for t in items if t.queue == filters.queue]
        if filters.search is not None:
            items = [t for t in items if filters.search in t.name]
        total = len(items)
        return items[offset : offset + limit], total

    async def get_task_by_id(self, task_id: str):
        for t in self._tasks:
            if t.id == task_id:
                return t
        return None

    async def retry_task(self, task_id: str) -> bool:
        task = await self.get_task_by_id(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        return True

    async def delete_task(self, task_id: str) -> bool:
        for i, t in enumerate(self._tasks):
            if t.id == task_id:
                del self._tasks[i]
                return True
        return False


@pytest.fixture
def sample_tasks():
    now = datetime.now(UTC)
    # Use model_validate to construct pydantic models from dicts and cast to Any
    t1 = cast(
        Any,
        Task.model_validate(
            {"id": "t1", "name": "task-one", "status": "pending", "queue": "q1", "enqueued_at": now}
        ),
    )
    t2 = cast(
        Any,
        Task.model_validate(
            {"id": "t2", "name": "task-two", "status": "failed", "queue": "q1", "enqueued_at": now}
        ),
    )
    t3 = cast(
        Any,
        Task.model_validate(
            {
                "id": "t3",
                "name": "other-task",
                "status": "completed",
                "queue": "q2",
                "enqueued_at": now,
            }
        ),
    )
    return [t1, t2, t3]


@pytest.fixture
def mock_task_service(sample_tasks):
    return MockTaskService(tasks=sample_tasks)


@pytest.fixture
def app(mock_task_service):
    app: FastAPI = create_monitoring_app()

    async def _override_get_task_service():
        return mock_task_service

    app.dependency_overrides[get_task_service] = _override_get_task_service
    return app


def pytest_configure(config):
    # expose test helpers under pytest.helpers for convenience
    import importlib.util
    from pathlib import Path

    helpers_path = Path(__file__).parent / "_helpers.py"
    spec = importlib.util.spec_from_file_location("test_helpers", helpers_path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load test helpers module")

    _helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_helpers)  # type: ignore[arg-type]

    # assign helpers to pytest namespace; use type-ignore for pyright
    if not hasattr(pytest, "helpers"):
        pytest.helpers = _helpers  # type: ignore[attr-defined]
