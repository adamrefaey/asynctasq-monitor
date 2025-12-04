"""Integration tests for Tasks API endpoints.

This module provides both sync and async integration tests for the tasks API.
Following pytest-asyncio best practices (2024):
- Use httpx.AsyncClient with ASGITransport for async tests
- Use @pytest.mark.asyncio for async tests (auto-applied in strict mode)
- Organize tests in classes for better structure and shared fixtures

References:
- FastAPI async tests: https://fastapi.tiangolo.com/advanced/async-tests/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/en/stable/
"""

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest

# =============================================================================
# Synchronous Integration Tests (with mocked services from root conftest)
# =============================================================================


@pytest.mark.integration
def test_list_tasks_basic(app):
    """Test listing all tasks returns expected count from shared fixtures."""
    with TestClient(app) as client:
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        # sample_tasks fixture provides 4 tasks
        assert data["total"] == 4


@pytest.mark.integration
def test_list_tasks_with_filters(app):
    """Test listing tasks with status and queue filters."""
    with TestClient(app) as client:
        # t2 is FAILED in 'payments' queue (not q1)
        resp = client.get("/api/tasks", params={"status": "failed", "queue": "payments"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == "t2"


@pytest.mark.integration
def test_get_task_found(app):
    with TestClient(app) as client:
        resp = client.get("/api/tasks/t1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "t1"


@pytest.mark.integration
def test_get_task_not_found(app):
    with TestClient(app) as client:
        resp = client.get("/api/tasks/missing")
        assert resp.status_code == 404


@pytest.mark.integration
def test_retry_task_success(app):
    with TestClient(app) as client:
        resp = client.post("/api/tasks/t2/retry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"


@pytest.mark.integration
def test_retry_task_fail(app):
    with TestClient(app) as client:
        resp = client.post("/api/tasks/t1/retry")
        assert resp.status_code == 400


@pytest.mark.integration
def test_delete_task_success_and_not_found(app):
    with TestClient(app) as client:
        resp = client.delete("/api/tasks/t1")
        assert resp.status_code == 200
        resp2 = client.delete("/api/tasks/t1")
        assert resp2.status_code == 404


# =============================================================================
# Async Integration Tests (following COMPLETION_PLAN Task 3.2 patterns)
# =============================================================================


@pytest.mark.integration
class TestTasksAPI:
    """Async integration tests for Tasks API.

    These tests use httpx.AsyncClient following FastAPI's recommended
    async testing pattern. They test against the app with mocked services
    using the async_client fixture from the root conftest.

    Note: Each async test method must be decorated with @pytest.mark.asyncio
    in strict mode. This is the recommended best practice as of pytest-asyncio 1.3.0.
    """

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, async_client: AsyncClient):
        """Test listing tasks returns proper response structure."""
        response = await async_client.get("/api/tasks")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        # Uses mocked service from root conftest which has 4 sample tasks
        assert data["total"] == 4

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, async_client: AsyncClient):
        """Test listing tasks with status, queue, and limit filters."""
        response = await async_client.get(
            "/api/tasks",
            params={"status": "pending", "queue": "emails", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 10
        # All returned items should match the filter
        for item in data["items"]:
            assert item["status"] == "pending"
            assert item["queue"] == "emails"

    @pytest.mark.asyncio
    async def test_list_tasks_with_search(self, async_client: AsyncClient):
        """Test listing tasks with search parameter."""
        response = await async_client.get(
            "/api/tasks",
            params={"search": "email"},
        )

        assert response.status_code == 200
        data = response.json()
        # Search should find tasks with 'email' in name
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_tasks_pagination(self, async_client: AsyncClient):
        """Test listing tasks with pagination parameters."""
        response = await async_client.get(
            "/api/tasks",
            params={"limit": 2, "offset": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

        # Get second page
        response2 = await async_client.get(
            "/api/tasks",
            params={"limit": 2, "offset": 2},
        )

        assert response2.status_code == 200
        data2 = response2.json()
        # Second page should have different items (or be empty)
        if data2["items"]:
            first_page_ids = {item["id"] for item in data["items"]}
            second_page_ids = {item["id"] for item in data2["items"]}
            assert first_page_ids.isdisjoint(second_page_ids)

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, async_client: AsyncClient):
        """Test retrieving a specific task by ID."""
        response = await async_client.get("/api/tasks/t1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "t1"
        assert "name" in data
        assert "status" in data
        assert "queue" in data

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, async_client: AsyncClient):
        """Test retrieving a non-existent task returns 404."""
        response = await async_client.get("/api/tasks/nonexistent-task-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_failed_task(self, async_client: AsyncClient):
        """Test retrying a failed task succeeds."""
        # t2 is a FAILED task from sample_tasks fixture
        response = await async_client.post("/api/tasks/t2/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_retry_non_failed_task(self, async_client: AsyncClient):
        """Test retrying a non-failed task returns error."""
        # t1 is a PENDING task from sample_tasks fixture
        response = await async_client.post("/api/tasks/t1/retry")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_nonexistent_task(self, async_client: AsyncClient):
        """Test retrying a non-existent task returns error.

        Note: The API returns 400 for all retry failures, including non-existent
        tasks, since the retry_task method returns False for both cases.
        """
        response = await async_client.post("/api/tasks/nonexistent/retry")

        # API returns 400 for any retry failure (not found or not retryable)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_task(self, async_client: AsyncClient):
        """Test deleting a task succeeds."""
        response = await async_client.delete("/api/tasks/t1")

        assert response.status_code == 200

        # Verify task is deleted
        response2 = await async_client.get("/api/tasks/t1")
        assert response2.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, async_client: AsyncClient):
        """Test deleting a non-existent task returns 404."""
        response = await async_client.delete("/api/tasks/nonexistent")

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "integration"])
