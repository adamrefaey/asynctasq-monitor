"""Integration tests for TaskService.

This module tests TaskService against a mocked BaseDriver to verify
the service layer correctly interacts with the driver layer.

Following 2024/2025 pytest best practices:
- Use pytest-asyncio strict mode with explicit @pytest.mark.asyncio
- Use factory fixtures for test data customization
- Follow AAA pattern (Arrange-Act-Assert)
- Test edge cases and error conditions
- Prefer integration tests over unit tests for service layers
- Use AsyncMock for async methods
- Group related tests using classes

References:
- https://pytest-with-eric.com/pytest-advanced/pytest-asyncio/
- https://asyncsquadlabs.com/blog/python-testing-best-practices/
- https://docs.pytest.org/en/stable/how-to/parametrize.html
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from asynctasq.core.dispatcher import Dispatcher
from asynctasq.core.models import TaskInfo
from asynctasq.drivers.base_driver import BaseDriver
from asynctasq_monitor.models.task import Task, TaskFilters, TaskStatus
from asynctasq_monitor.services.task_service import TaskService

pytestmark = pytest.mark.asyncio


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_driver() -> MagicMock:
    """Create a mock BaseDriver for testing."""
    driver = MagicMock(spec=BaseDriver)
    driver.get_tasks = AsyncMock(return_value=([], 0))
    driver.get_task_by_id = AsyncMock(return_value=None)
    driver.retry_task = AsyncMock(return_value=False)
    driver.delete_task = AsyncMock(return_value=False)
    return driver


@pytest.fixture
def mock_dispatcher(mock_driver: MagicMock) -> MagicMock:
    """Create a mock Dispatcher with the mock driver attached."""
    dispatcher = MagicMock(spec=Dispatcher)
    dispatcher.driver = mock_driver
    return dispatcher


@pytest_asyncio.fixture
async def task_service(mock_dispatcher: MagicMock) -> TaskService:
    """Create a TaskService with mocked dispatcher."""
    service = TaskService()
    with patch(
        "asynctasq_monitor.services.task_service.get_dispatcher",
        return_value=mock_dispatcher,
    ):
        # Force driver initialization by calling _ensure_driver
        service._ensure_driver()
    return service


@pytest.fixture
def task_info_factory() -> Any:
    """Factory for creating TaskInfo test data with customizable fields."""

    def _factory(
        *,
        id: str = "task-123",
        name: str = "test_task",
        queue: str = "default",
        status: str = "pending",
        enqueued_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_ms: int | None = None,
        worker_id: str | None = None,
        attempt: int = 1,
        max_retries: int = 3,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        result: Any = None,
        exception: str | None = None,
        traceback: str | None = None,
        priority: int = 0,
        timeout_seconds: int | None = None,
        tags: list[str] | None = None,
    ) -> TaskInfo:
        return TaskInfo(
            id=id,
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

    return _factory


# ============================================================================
# Test Class: _ensure_driver
# ============================================================================


class TestEnsureDriver:
    """Tests for TaskService._ensure_driver method."""

    async def test_ensure_driver_sets_driver_from_dispatcher(
        self,
        mock_dispatcher: MagicMock,
    ) -> None:
        """_ensure_driver should get driver from dispatcher on first call."""
        # Arrange
        service = TaskService()
        assert service._driver is None

        # Act
        with patch(
            "asynctasq_monitor.services.task_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            service._ensure_driver()

        # Assert
        assert service._driver is mock_dispatcher.driver

    async def test_ensure_driver_caches_driver(
        self,
        mock_dispatcher: MagicMock,
    ) -> None:
        """_ensure_driver should not re-fetch driver if already set."""
        # Arrange
        service = TaskService()
        original_driver = MagicMock(spec=BaseDriver)
        service._driver = original_driver

        # Act
        with patch(
            "asynctasq_monitor.services.task_service.get_dispatcher",
            return_value=mock_dispatcher,
        ) as mock_get_dispatcher:
            service._ensure_driver()

        # Assert - driver unchanged, get_dispatcher not called
        assert service._driver is original_driver
        mock_get_dispatcher.assert_not_called()

    async def test_ensure_driver_raises_when_dispatcher_none(self) -> None:
        """_ensure_driver should raise RuntimeError when dispatcher is None."""
        # Arrange
        service = TaskService()

        # Act & Assert
        with patch(
            "asynctasq_monitor.services.task_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                service._ensure_driver()

    async def test_ensure_driver_raises_when_dispatcher_has_no_driver(self) -> None:
        """_ensure_driver should raise RuntimeError when dispatcher has no driver."""
        # Arrange
        service = TaskService()
        dispatcher_without_driver = MagicMock()
        del dispatcher_without_driver.driver  # Remove driver attribute

        # Act & Assert
        with patch(
            "asynctasq_monitor.services.task_service.get_dispatcher",
            return_value=dispatcher_without_driver,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                service._ensure_driver()


# ============================================================================
# Test Class: get_tasks
# ============================================================================


class TestGetTasks:
    """Tests for TaskService.get_tasks method."""

    async def test_get_tasks_returns_empty_list_when_no_tasks(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """get_tasks should return empty list and zero total when no tasks exist."""
        # Arrange
        mock_driver.get_tasks.return_value = ([], 0)
        filters = TaskFilters()

        # Act
        tasks, total = await task_service.get_tasks(filters)

        # Assert
        assert tasks == []
        assert total == 0
        mock_driver.get_tasks.assert_awaited_once()

    async def test_get_tasks_converts_task_info_to_task_models(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """get_tasks should convert TaskInfo objects to Task models."""
        # Arrange
        task_infos = [
            task_info_factory(id="task-1", name="task_one", status="pending"),
            task_info_factory(id="task-2", name="task_two", status="completed"),
        ]
        mock_driver.get_tasks.return_value = (task_infos, 2)
        filters = TaskFilters()

        # Act
        tasks, total = await task_service.get_tasks(filters)

        # Assert
        assert len(tasks) == 2
        assert total == 2
        assert all(isinstance(t, Task) for t in tasks)
        assert tasks[0].id == "task-1"
        assert tasks[0].name == "task_one"
        assert tasks[0].status == TaskStatus.PENDING
        assert tasks[1].id == "task-2"
        assert tasks[1].status == TaskStatus.COMPLETED

    async def test_get_tasks_passes_status_filter_to_driver(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """get_tasks should pass status filter value to driver."""
        # Arrange
        filters = TaskFilters(status=TaskStatus.RUNNING)

        # Act
        await task_service.get_tasks(filters)

        # Assert
        mock_driver.get_tasks.assert_awaited_once_with(
            status="running",
            queue=None,
            worker_id=None,
            limit=50,
            offset=0,
        )

    async def test_get_tasks_passes_queue_filter_to_driver(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """get_tasks should pass queue filter to driver."""
        # Arrange
        filters = TaskFilters(queue="emails")

        # Act
        await task_service.get_tasks(filters)

        # Assert
        mock_driver.get_tasks.assert_awaited_once_with(
            status=None,
            queue="emails",
            worker_id=None,
            limit=50,
            offset=0,
        )

    async def test_get_tasks_passes_worker_id_filter_to_driver(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """get_tasks should pass worker_id filter to driver."""
        # Arrange
        filters = TaskFilters(worker_id="worker-abc")

        # Act
        await task_service.get_tasks(filters)

        # Assert
        mock_driver.get_tasks.assert_awaited_once_with(
            status=None,
            queue=None,
            worker_id="worker-abc",
            limit=50,
            offset=0,
        )

    async def test_get_tasks_passes_all_filters_to_driver(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """get_tasks should pass all filters to driver simultaneously."""
        # Arrange
        filters = TaskFilters(
            status=TaskStatus.FAILED,
            queue="notifications",
            worker_id="worker-xyz",
        )

        # Act
        await task_service.get_tasks(filters, limit=25, offset=10)

        # Assert
        mock_driver.get_tasks.assert_awaited_once_with(
            status="failed",
            queue="notifications",
            worker_id="worker-xyz",
            limit=25,
            offset=10,
        )

    async def test_get_tasks_respects_pagination_parameters(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """get_tasks should pass limit and offset to driver."""
        # Arrange
        filters = TaskFilters()

        # Act
        await task_service.get_tasks(filters, limit=100, offset=50)

        # Assert
        mock_driver.get_tasks.assert_awaited_once_with(
            status=None,
            queue=None,
            worker_id=None,
            limit=100,
            offset=50,
        )

    async def test_get_tasks_raises_runtime_error_when_driver_not_initialized(
        self,
    ) -> None:
        """get_tasks should raise RuntimeError when driver is not initialized."""
        # Arrange
        service = TaskService()
        service._driver = None
        filters = TaskFilters()

        # Act & Assert - patch _ensure_driver to do nothing (simulating failure)
        with patch.object(service, "_ensure_driver", lambda: None):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.get_tasks(filters)

    @pytest.mark.parametrize(
        "status",
        [
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.RETRYING,
            TaskStatus.CANCELLED,
        ],
    )
    async def test_get_tasks_handles_all_task_statuses(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
        status: TaskStatus,
    ) -> None:
        """get_tasks should correctly handle all possible task statuses."""
        # Arrange
        task_info = task_info_factory(id=f"task-{status.value}", status=status.value)
        mock_driver.get_tasks.return_value = ([task_info], 1)
        filters = TaskFilters()

        # Act
        tasks, total = await task_service.get_tasks(filters)

        # Assert
        assert len(tasks) == 1
        assert tasks[0].status == status

    async def test_get_tasks_preserves_task_metadata(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """get_tasks should preserve all task metadata during conversion."""
        # Arrange
        now = datetime.now(UTC)
        task_info = task_info_factory(
            id="task-full",
            name="full_task",
            queue="high-priority",
            status="completed",
            enqueued_at=now - timedelta(minutes=5),
            started_at=now - timedelta(minutes=4),
            completed_at=now,
            duration_ms=60000,
            worker_id="worker-1",
            attempt=2,
            max_retries=5,
            args=["arg1", 123],
            kwargs={"key": "value"},
            result={"success": True},
            priority=10,
            timeout_seconds=300,
            tags=["important", "email"],
        )
        mock_driver.get_tasks.return_value = ([task_info], 1)
        filters = TaskFilters()

        # Act
        tasks, _ = await task_service.get_tasks(filters)

        # Assert
        task = tasks[0]
        assert task.id == "task-full"
        assert task.name == "full_task"
        assert task.queue == "high-priority"
        assert task.status == TaskStatus.COMPLETED
        assert task.duration_ms == 60000
        assert task.worker_id == "worker-1"
        assert task.attempt == 2
        assert task.max_retries == 5
        assert task.args == ["arg1", 123]
        assert task.kwargs == {"key": "value"}
        assert task.result == {"success": True}
        assert task.priority == 10
        assert task.timeout_seconds == 300
        assert task.tags == ["important", "email"]


# ============================================================================
# Test Class: get_task_by_id
# ============================================================================


class TestGetTaskById:
    """Tests for TaskService.get_task_by_id method."""

    async def test_get_task_by_id_returns_task_when_found(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """get_task_by_id should return Task model when task exists."""
        # Arrange
        task_info = task_info_factory(id="task-abc", name="found_task")
        mock_driver.get_task_by_id.return_value = task_info

        # Act
        task = await task_service.get_task_by_id("task-abc")

        # Assert
        assert task is not None
        assert isinstance(task, Task)
        assert task.id == "task-abc"
        assert task.name == "found_task"
        mock_driver.get_task_by_id.assert_awaited_once_with("task-abc")

    async def test_get_task_by_id_returns_none_when_not_found(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """get_task_by_id should return None when task doesn't exist."""
        # Arrange
        mock_driver.get_task_by_id.return_value = None

        # Act
        task = await task_service.get_task_by_id("nonexistent-task")

        # Assert
        assert task is None
        mock_driver.get_task_by_id.assert_awaited_once_with("nonexistent-task")

    async def test_get_task_by_id_raises_runtime_error_when_driver_not_initialized(
        self,
    ) -> None:
        """get_task_by_id should raise RuntimeError when driver is not initialized."""
        # Arrange
        service = TaskService()
        service._driver = None

        # Act & Assert
        with patch.object(service, "_ensure_driver", lambda: None):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.get_task_by_id("any-id")

    async def test_get_task_by_id_preserves_error_information(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """get_task_by_id should preserve exception and traceback for failed tasks."""
        # Arrange
        task_info = task_info_factory(
            id="failed-task",
            status="failed",
            exception="ValueError: Invalid input",
            traceback="Traceback (most recent call last):\n  File...",
        )
        mock_driver.get_task_by_id.return_value = task_info

        # Act
        task = await task_service.get_task_by_id("failed-task")

        # Assert
        assert task is not None
        assert task.status == TaskStatus.FAILED
        assert task.exception == "ValueError: Invalid input"
        assert task.traceback is not None
        assert "Traceback" in task.traceback

    async def test_get_task_by_id_with_uuid_format(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """get_task_by_id should work with UUID-formatted task IDs."""
        # Arrange
        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        task_info = task_info_factory(id=uuid_id)
        mock_driver.get_task_by_id.return_value = task_info

        # Act
        task = await task_service.get_task_by_id(uuid_id)

        # Assert
        assert task is not None
        assert task.id == uuid_id


# ============================================================================
# Test Class: retry_task
# ============================================================================


class TestRetryTask:
    """Tests for TaskService.retry_task method."""

    async def test_retry_task_returns_true_on_success(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """retry_task should return True when driver successfully retries."""
        # Arrange
        mock_driver.retry_task.return_value = True

        # Act
        result = await task_service.retry_task("task-to-retry")

        # Assert
        assert result is True
        mock_driver.retry_task.assert_awaited_once_with("task-to-retry")

    async def test_retry_task_returns_false_on_failure(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """retry_task should return False when driver cannot retry task."""
        # Arrange
        mock_driver.retry_task.return_value = False

        # Act
        result = await task_service.retry_task("non-retryable-task")

        # Assert
        assert result is False
        mock_driver.retry_task.assert_awaited_once_with("non-retryable-task")

    async def test_retry_task_raises_runtime_error_when_driver_not_initialized(
        self,
    ) -> None:
        """retry_task should raise RuntimeError when driver is not initialized."""
        # Arrange
        service = TaskService()
        service._driver = None

        # Act & Assert
        with patch.object(service, "_ensure_driver", lambda: None):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.retry_task("any-id")

    async def test_retry_task_with_nonexistent_task(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """retry_task should return False for nonexistent task ID."""
        # Arrange
        mock_driver.retry_task.return_value = False

        # Act
        result = await task_service.retry_task("nonexistent-task-id")

        # Assert
        assert result is False

    async def test_retry_task_passes_task_id_correctly(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """retry_task should pass the exact task_id to driver."""
        # Arrange
        task_id = "specific-task-id-12345"
        mock_driver.retry_task.return_value = True

        # Act
        await task_service.retry_task(task_id)

        # Assert
        mock_driver.retry_task.assert_awaited_once_with(task_id)


# ============================================================================
# Test Class: delete_task
# ============================================================================


class TestDeleteTask:
    """Tests for TaskService.delete_task method."""

    async def test_delete_task_returns_true_on_success(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """delete_task should return True when driver successfully deletes."""
        # Arrange
        mock_driver.delete_task.return_value = True

        # Act
        result = await task_service.delete_task("task-to-delete")

        # Assert
        assert result is True
        mock_driver.delete_task.assert_awaited_once_with("task-to-delete")

    async def test_delete_task_returns_false_when_not_found(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """delete_task should return False when task doesn't exist."""
        # Arrange
        mock_driver.delete_task.return_value = False

        # Act
        result = await task_service.delete_task("nonexistent-task")

        # Assert
        assert result is False
        mock_driver.delete_task.assert_awaited_once_with("nonexistent-task")

    async def test_delete_task_raises_runtime_error_when_driver_not_initialized(
        self,
    ) -> None:
        """delete_task should raise RuntimeError when driver is not initialized."""
        # Arrange
        service = TaskService()
        service._driver = None

        # Act & Assert
        with patch.object(service, "_ensure_driver", lambda: None):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.delete_task("any-id")

    async def test_delete_task_passes_task_id_correctly(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """delete_task should pass the exact task_id to driver."""
        # Arrange
        task_id = "uuid-formatted-task-id"
        mock_driver.delete_task.return_value = True

        # Act
        await task_service.delete_task(task_id)

        # Assert
        mock_driver.delete_task.assert_awaited_once_with(task_id)


# ============================================================================
# Test Class: Integration Edge Cases
# ============================================================================


class TestIntegrationEdgeCases:
    """Integration tests for edge cases and complex scenarios."""

    async def test_service_handles_large_task_list(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """Service should handle large number of tasks efficiently."""
        # Arrange
        task_infos = [task_info_factory(id=f"task-{i}", name=f"task_{i}") for i in range(500)]
        mock_driver.get_tasks.return_value = (task_infos, 500)
        filters = TaskFilters()

        # Act
        tasks, total = await task_service.get_tasks(filters, limit=500)

        # Assert
        assert len(tasks) == 500
        assert total == 500
        assert all(isinstance(t, Task) for t in tasks)

    async def test_service_handles_task_with_minimal_data(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """Service should handle tasks with only required fields."""
        # Arrange
        minimal_task_info = TaskInfo(
            id="minimal-task",
            name="minimal",
            queue="default",
            status="pending",
            enqueued_at=datetime.now(UTC),
        )
        mock_driver.get_tasks.return_value = ([minimal_task_info], 1)
        filters = TaskFilters()

        # Act
        tasks, _ = await task_service.get_tasks(filters)

        # Assert
        task = tasks[0]
        assert task.id == "minimal-task"
        assert task.started_at is None
        assert task.completed_at is None
        assert task.duration_ms is None
        assert task.worker_id is None
        assert task.args == []
        assert task.kwargs == {}

    async def test_service_handles_task_with_complex_result(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """Service should handle tasks with complex nested result data."""
        # Arrange
        complex_result = {
            "data": [1, 2, 3],
            "nested": {"deep": {"value": True}},
            "list_of_dicts": [{"a": 1}, {"b": 2}],
        }
        task_info = task_info_factory(
            id="complex-result-task",
            status="completed",
            result=complex_result,
        )
        mock_driver.get_task_by_id.return_value = task_info

        # Act
        task = await task_service.get_task_by_id("complex-result-task")

        # Assert
        assert task is not None
        assert task.result == complex_result

    async def test_service_handles_empty_string_task_id(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """Service should pass empty string task_id to driver."""
        # Arrange
        mock_driver.get_task_by_id.return_value = None

        # Act
        task = await task_service.get_task_by_id("")

        # Assert
        assert task is None
        mock_driver.get_task_by_id.assert_awaited_once_with("")

    async def test_service_preserves_special_characters_in_task_data(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """Service should preserve special characters in task args/kwargs."""
        # Arrange
        special_args = ["hello\nworld", "tab\there", "unicode: 日本語"]
        special_kwargs = {"key": "value with 'quotes'", "emoji": "🎉"}
        task_info = task_info_factory(
            id="special-chars-task",
            args=special_args,
            kwargs=special_kwargs,
        )
        mock_driver.get_task_by_id.return_value = task_info

        # Act
        task = await task_service.get_task_by_id("special-chars-task")

        # Assert
        assert task is not None
        assert task.args == special_args
        assert task.kwargs == special_kwargs

    async def test_multiple_operations_on_same_service_instance(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """Service should handle multiple operations sequentially."""
        # Arrange
        task_info = task_info_factory(id="test-task")
        mock_driver.get_tasks.return_value = ([task_info], 1)
        mock_driver.get_task_by_id.return_value = task_info
        mock_driver.retry_task.return_value = True
        mock_driver.delete_task.return_value = True
        filters = TaskFilters()

        # Act - Multiple operations
        tasks, _ = await task_service.get_tasks(filters)
        task = await task_service.get_task_by_id("test-task")
        retry_result = await task_service.retry_task("test-task")
        delete_result = await task_service.delete_task("test-task")

        # Assert
        assert len(tasks) == 1
        assert task is not None
        assert retry_result is True
        assert delete_result is True

    async def test_service_handles_none_status_in_filters(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
    ) -> None:
        """Service should pass None status correctly when not specified."""
        # Arrange
        filters = TaskFilters(status=None, queue="test-queue")

        # Act
        await task_service.get_tasks(filters)

        # Assert
        mock_driver.get_tasks.assert_awaited_once_with(
            status=None,
            queue="test-queue",
            worker_id=None,
            limit=50,
            offset=0,
        )

    async def test_service_computed_fields_work_correctly(
        self,
        task_service: TaskService,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """Service should return tasks with working computed fields."""
        # Arrange
        task_info = task_info_factory(
            id="computed-task",
            status="failed",
            attempt=2,
            max_retries=5,
            duration_ms=2500,
        )
        mock_driver.get_task_by_id.return_value = task_info

        # Act
        task = await task_service.get_task_by_id("computed-task")

        # Assert
        assert task is not None
        assert task.is_retryable is True  # failed and attempt < max_retries
        assert task.has_error is True  # status is failed
        assert task.duration_seconds == 2.5  # 2500ms = 2.5s

    async def test_service_handles_concurrent_driver_access(
        self,
        mock_dispatcher: MagicMock,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """Service should handle driver being set during operations."""
        # Arrange
        service = TaskService()
        task_info = task_info_factory(id="concurrent-task")
        mock_driver.get_task_by_id.return_value = task_info

        # Simulate driver being set by _ensure_driver during first access
        original_ensure = service._ensure_driver

        def patched_ensure() -> None:
            with patch(
                "asynctasq_monitor.services.task_service.get_dispatcher",
                return_value=mock_dispatcher,
            ):
                original_ensure()

        # Act
        with patch.object(service, "_ensure_driver", patched_ensure):
            task = await service.get_task_by_id("concurrent-task")

        # Assert
        assert task is not None
        assert task.id == "concurrent-task"


# ============================================================================
# Test Class: Initialization
# ============================================================================


class TestTaskServiceInitialization:
    """Tests for TaskService initialization."""

    async def test_init_creates_service_with_no_driver(self) -> None:
        """TaskService should initialize with _driver set to None."""
        # Act
        service = TaskService()

        # Assert
        assert service._driver is None

    async def test_service_lazily_initializes_driver(
        self,
        mock_dispatcher: MagicMock,
        mock_driver: MagicMock,
        task_info_factory: Any,
    ) -> None:
        """Service should initialize driver on first operation."""
        # Arrange
        service = TaskService()
        mock_driver.get_tasks.return_value = ([], 0)
        filters = TaskFilters()

        # Act
        with patch(
            "asynctasq_monitor.services.task_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            await service.get_tasks(filters)

        # Assert
        assert service._driver is mock_dispatcher.driver
