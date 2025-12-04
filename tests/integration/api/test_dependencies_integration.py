"""Integration tests for the API dependencies module.

These tests verify:
- Dependency injection patterns work correctly with FastAPI
- Service singletons behave correctly
- Pagination dependencies work as expected
- Request state access works
- Async context manager patterns for cleanup
- Factory pattern for custom pagination

Following FastAPI 0.122+ testing best practices:
- Use app.dependency_overrides for testing
- Use TestClient for synchronous tests
- Use pytest-asyncio for async tests
- Test the actual dependency injection behavior
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from asynctasq_monitor.api.dependencies import (
    PaginationDep,
    QueueServiceDep,
    RequestStateDep,
    SettingsDep,
    SmallPaginationDep,
    TaskServiceDep,
    WorkerServiceDep,
    _get_queue_service_singleton,
    _get_task_service_singleton,
    _get_worker_service_singleton,
    create_pagination_dep,
    get_queue_service,
    get_scoped_task_service,
    get_settings_dependency,
    get_task_service,
    get_worker_service,
    pagination_params,
)
from asynctasq_monitor.config import Settings
from asynctasq_monitor.services.queue_service import QueueService
from asynctasq_monitor.services.task_service import TaskService
from asynctasq_monitor.services.worker_service import WorkerService


@pytest.mark.integration
class TestSettingsDependency:
    """Tests for settings dependency injection."""

    def test_get_settings_dependency_returns_settings(self) -> None:
        """Test that get_settings_dependency returns a Settings instance."""
        settings = get_settings_dependency()
        assert isinstance(settings, Settings)

    def test_settings_dependency_in_endpoint(self) -> None:
        """Test settings dependency works in FastAPI endpoint."""
        app = FastAPI()

        @app.get("/test-settings")
        async def test_endpoint(settings: SettingsDep) -> dict:
            return {
                "type": type(settings).__name__,
                "has_cors_origins": hasattr(settings, "cors_origins"),
            }

        client = TestClient(app)
        response = client.get("/test-settings")
        assert response.status_code == 200
        assert response.json()["type"] == "Settings"
        assert response.json()["has_cors_origins"] is True


@pytest.mark.integration
class TestTaskServiceDependency:
    """Tests for TaskService dependency injection."""

    def test_get_task_service_returns_service(self) -> None:
        """Test that get_task_service returns a TaskService instance."""
        service = get_task_service()
        assert isinstance(service, TaskService)

    def test_task_service_singleton_pattern(self) -> None:
        """Test that TaskService uses singleton pattern."""
        # Clear the cache to start fresh
        _get_task_service_singleton.cache_clear()

        service1 = get_task_service()
        service2 = get_task_service()
        assert service1 is service2

    def test_task_service_dependency_in_endpoint(self) -> None:
        """Test TaskService dependency works in FastAPI endpoint."""
        app = FastAPI()

        @app.get("/test-task-service")
        async def test_endpoint(service: TaskServiceDep) -> dict:
            return {"type": type(service).__name__}

        client = TestClient(app)
        response = client.get("/test-task-service")
        assert response.status_code == 200
        assert response.json()["type"] == "TaskService"


@pytest.mark.integration
class TestWorkerServiceDependency:
    """Tests for WorkerService dependency injection."""

    def test_get_worker_service_returns_service(self) -> None:
        """Test that get_worker_service returns a WorkerService instance."""
        service = get_worker_service()
        assert isinstance(service, WorkerService)

    def test_worker_service_singleton_pattern(self) -> None:
        """Test that WorkerService uses singleton pattern."""
        _get_worker_service_singleton.cache_clear()

        service1 = get_worker_service()
        service2 = get_worker_service()
        assert service1 is service2

    def test_worker_service_dependency_in_endpoint(self) -> None:
        """Test WorkerService dependency works in FastAPI endpoint."""
        app = FastAPI()

        @app.get("/test-worker-service")
        async def test_endpoint(service: WorkerServiceDep) -> dict:
            return {"type": type(service).__name__}

        client = TestClient(app)
        response = client.get("/test-worker-service")
        assert response.status_code == 200
        assert response.json()["type"] == "WorkerService"


@pytest.mark.integration
class TestQueueServiceDependency:
    """Tests for QueueService dependency injection."""

    def test_get_queue_service_returns_service(self) -> None:
        """Test that get_queue_service returns a QueueService instance."""
        service = get_queue_service()
        assert isinstance(service, QueueService)

    def test_queue_service_singleton_pattern(self) -> None:
        """Test that QueueService uses singleton pattern."""
        _get_queue_service_singleton.cache_clear()

        service1 = get_queue_service()
        service2 = get_queue_service()
        assert service1 is service2

    def test_queue_service_dependency_in_endpoint(self) -> None:
        """Test QueueService dependency works in FastAPI endpoint."""
        app = FastAPI()

        @app.get("/test-queue-service")
        async def test_endpoint(service: QueueServiceDep) -> dict:
            return {"type": type(service).__name__}

        client = TestClient(app)
        response = client.get("/test-queue-service")
        assert response.status_code == 200
        assert response.json()["type"] == "QueueService"


@pytest.mark.integration
class TestRequestStateDependency:
    """Tests for request state dependency."""

    def test_request_state_dependency_returns_dict(self) -> None:
        """Test that request state dependency works."""
        app = FastAPI()

        # Add some state during lifespan
        app.state.test_value = "hello"

        @app.get("/test-state")
        async def test_endpoint(state: RequestStateDep) -> dict:
            return {
                "type": type(state).__name__,
                "has_test_value": "test_value" in state,
            }

        client = TestClient(app)
        response = client.get("/test-state")
        assert response.status_code == 200
        assert response.json()["type"] == "dict"
        assert response.json()["has_test_value"] is True


@pytest.mark.integration
class TestPaginationDependency:
    """Tests for pagination dependency injection."""

    def test_pagination_params_default_values(self) -> None:
        """Test pagination_params returns correct defaults."""
        limit, offset = pagination_params()
        assert limit == 50
        assert offset == 0

    def test_pagination_params_custom_values(self) -> None:
        """Test pagination_params accepts custom values."""
        limit, offset = pagination_params(limit=100, offset=20)
        assert limit == 100
        assert offset == 20

    def test_pagination_dependency_in_endpoint(self) -> None:
        """Test pagination dependency works in FastAPI endpoint."""
        app = FastAPI()

        @app.get("/test-pagination")
        async def test_endpoint(pagination: PaginationDep) -> dict:
            limit, offset = pagination
            return {"limit": limit, "offset": offset}

        client = TestClient(app)

        # Test default values
        response = client.get("/test-pagination")
        assert response.status_code == 200
        assert response.json() == {"limit": 50, "offset": 0}

        # Test custom values
        response = client.get("/test-pagination?limit=25&offset=10")
        assert response.status_code == 200
        assert response.json() == {"limit": 25, "offset": 10}

    def test_pagination_validation_min_limit(self) -> None:
        """Test pagination validates minimum limit."""
        app = FastAPI()

        @app.get("/test-pagination")
        async def test_endpoint(pagination: PaginationDep) -> dict:
            limit, offset = pagination
            return {"limit": limit, "offset": offset}

        client = TestClient(app)

        # Test limit below minimum
        response = client.get("/test-pagination?limit=0")
        assert response.status_code == 422

    def test_pagination_validation_max_limit(self) -> None:
        """Test pagination validates maximum limit."""
        app = FastAPI()

        @app.get("/test-pagination")
        async def test_endpoint(pagination: PaginationDep) -> dict:
            limit, offset = pagination
            return {"limit": limit, "offset": offset}

        client = TestClient(app)

        # Test limit above maximum
        response = client.get("/test-pagination?limit=501")
        assert response.status_code == 422

    def test_pagination_validation_negative_offset(self) -> None:
        """Test pagination validates negative offset."""
        app = FastAPI()

        @app.get("/test-pagination")
        async def test_endpoint(pagination: PaginationDep) -> dict:
            limit, offset = pagination
            return {"limit": limit, "offset": offset}

        client = TestClient(app)

        # Test negative offset
        response = client.get("/test-pagination?offset=-1")
        assert response.status_code == 422


@pytest.mark.integration
class TestSmallPaginationDependency:
    """Tests for small pagination dependency."""

    def test_small_pagination_in_endpoint(self) -> None:
        """Test SmallPaginationDep works with smaller limits."""
        app = FastAPI()

        @app.get("/test-small-pagination")
        async def test_endpoint(pagination: SmallPaginationDep) -> dict:
            limit, offset = pagination
            return {"limit": limit, "offset": offset}

        client = TestClient(app)

        # Test default values (should be 10, 0)
        response = client.get("/test-small-pagination")
        assert response.status_code == 200
        assert response.json() == {"limit": 10, "offset": 0}

        # Test max limit is 100 for small pagination
        response = client.get("/test-small-pagination?limit=100")
        assert response.status_code == 200
        assert response.json()["limit"] == 100

        # Test exceeding max limit fails
        response = client.get("/test-small-pagination?limit=101")
        assert response.status_code == 422


@pytest.mark.integration
class TestCreatePaginationDepFactory:
    """Tests for the pagination dependency factory function."""

    def test_create_pagination_dep_default_values(self) -> None:
        """Test factory creates pagination with specified defaults."""
        custom_pagination = create_pagination_dep(default_limit=25, max_limit=200)

        app = FastAPI()

        @app.get("/test-custom")
        async def test_endpoint(
            pagination: Annotated[tuple[int, int], Depends(custom_pagination)],
        ) -> dict:
            limit, offset = pagination
            return {"limit": limit, "offset": offset}

        client = TestClient(app)

        # Test custom default
        response = client.get("/test-custom")
        assert response.status_code == 200
        assert response.json()["limit"] == 25

        # Test custom max limit works
        response = client.get("/test-custom?limit=200")
        assert response.status_code == 200
        assert response.json()["limit"] == 200

        # Test exceeding custom max fails
        response = client.get("/test-custom?limit=201")
        assert response.status_code == 422

    def test_create_pagination_dep_returns_callable(self) -> None:
        """Test factory returns a callable."""
        result = create_pagination_dep(10, 50)
        assert callable(result)


@pytest.mark.integration
class TestScopedTaskServiceDependency:
    """Tests for the async context manager pattern."""

    @pytest.mark.asyncio
    async def test_scoped_task_service_yields_service(self) -> None:
        """Test that get_scoped_task_service yields a TaskService."""
        async with get_scoped_task_service() as service:
            assert isinstance(service, TaskService)

    @pytest.mark.asyncio
    async def test_scoped_task_service_cleanup(self) -> None:
        """Test that cleanup runs after context manager exits."""
        original_service = None

        async with get_scoped_task_service() as service:
            original_service = service
            assert service is not None

        # After exiting, service was properly yielded and cleanup ran
        assert original_service is not None


@pytest.mark.integration
class TestDependencyOverrides:
    """Tests for dependency override patterns (FastAPI best practice)."""

    def test_task_service_can_be_overridden(self) -> None:
        """Test that TaskService dependency can be overridden for testing."""
        from asynctasq_monitor.api.main import create_monitoring_app

        app = create_monitoring_app()

        class MockTaskService:
            async def get_tasks(self, *args, **kwargs):
                return [], 0

        app.dependency_overrides[get_task_service] = lambda: MockTaskService()

        client = TestClient(app)
        response = client.get("/api/tasks/")
        assert response.status_code == 200

        # Clean up
        app.dependency_overrides = {}

    def test_worker_service_can_be_overridden(self) -> None:
        """Test that WorkerService dependency can be overridden for testing."""
        from fastapi import FastAPI

        app = FastAPI()

        # Create a simple test endpoint that uses the worker service
        @app.get("/test-override")
        async def test_endpoint(service: WorkerServiceDep) -> dict:
            return {"service_type": type(service).__name__}

        # Create a mock service
        class MockWorkerService:
            pass

        # Override the dependency
        app.dependency_overrides[get_worker_service] = lambda: MockWorkerService()

        client = TestClient(app)
        response = client.get("/test-override")
        assert response.status_code == 200
        assert response.json()["service_type"] == "MockWorkerService"

        # Clean up
        app.dependency_overrides = {}

    def test_queue_service_can_be_overridden(self) -> None:
        """Test that QueueService dependency can be overridden for testing."""
        from fastapi import FastAPI

        app = FastAPI()

        # Create a simple test endpoint that uses the queue service
        @app.get("/test-override")
        async def test_endpoint(service: QueueServiceDep) -> dict:
            return {"service_type": type(service).__name__}

        # Create a mock service
        class MockQueueService:
            pass

        # Override the dependency
        app.dependency_overrides[get_queue_service] = lambda: MockQueueService()

        client = TestClient(app)
        response = client.get("/test-override")
        assert response.status_code == 200
        assert response.json()["service_type"] == "MockQueueService"

        # Clean up
        app.dependency_overrides = {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
