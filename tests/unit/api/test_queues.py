"""Unit tests for queue API routes.

Tests the /api/queues/* endpoints with MockQueueService from conftest.
Follows pytest best practices and Week 6 implementation specifications.
"""

from httpx import AsyncClient
import pytest

pytestmark = pytest.mark.asyncio


# ============================================================================
# Tests: GET /queues
# ============================================================================


class TestListQueues:
    """Tests for GET /api/queues endpoint."""

    async def test_list_queues_returns_all_queues(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that listing queues returns all queues."""
        response = await async_client.get("/api/queues")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 4
        assert data["total"] == 4

    async def test_list_queues_with_status_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering queues by status."""
        response = await async_client.get("/api/queues?status=active")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 3
        for queue in data["items"]:
            assert queue["status"] == "active"

    async def test_list_queues_with_paused_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering for paused queues."""
        response = await async_client.get("/api/queues?status=paused")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "payments"
        assert data["items"][0]["status"] == "paused"

    async def test_list_queues_with_search(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test searching queues by name."""
        response = await async_client.get("/api/queues?search=email")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "emails"

    async def test_list_queues_with_min_depth_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering queues by minimum depth."""
        response = await async_client.get("/api/queues?min_depth=100")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 2  # reports (150) and notifications (550)
        for queue in data["items"]:
            assert queue["depth"] >= 100

    async def test_list_queues_with_alert_level_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering queues by alert level."""
        response = await async_client.get("/api/queues?alert_level=critical")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "notifications"
        assert data["items"][0]["alert_level"] == "critical"

    async def test_list_queues_contains_computed_fields(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that queue responses include computed fields."""
        response = await async_client.get("/api/queues")
        assert response.status_code == 200

        data = response.json()
        queue = data["items"][0]

        # Check computed fields are present
        assert "alert_level" in queue
        assert "total_tasks" in queue
        assert "success_rate" in queue
        assert "is_idle" in queue


# ============================================================================
# Tests: GET /queues/{name}
# ============================================================================


class TestGetQueue:
    """Tests for GET /api/queues/{name} endpoint."""

    async def test_get_queue_by_name(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test getting a specific queue by name."""
        response = await async_client.get("/api/queues/emails")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "emails"
        assert data["status"] == "active"
        assert data["depth"] == 42
        assert data["processing"] == 5
        assert data["workers_assigned"] == 3

    async def test_get_queue_not_found(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test 404 for non-existent queue."""
        response = await async_client.get("/api/queues/nonexistent")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    async def test_get_paused_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test getting a paused queue includes paused_at timestamp."""
        response = await async_client.get("/api/queues/payments")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "payments"
        assert data["status"] == "paused"
        assert data["paused_at"] is not None


# ============================================================================
# Tests: GET /queues/{name}/metrics
# ============================================================================


class TestGetQueueMetrics:
    """Tests for GET /api/queues/{name}/metrics endpoint."""

    async def test_get_queue_metrics(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test getting metrics for a queue."""
        response = await async_client.get("/api/queues/emails/metrics")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    async def test_get_queue_metrics_not_found(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test 404 for metrics of non-existent queue."""
        response = await async_client.get("/api/queues/nonexistent/metrics")
        assert response.status_code == 404


# ============================================================================
# Tests: Queue Actions
# ============================================================================


class TestPauseQueue:
    """Tests for POST /api/queues/{name}/pause endpoint."""

    async def test_pause_active_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test pausing an active queue."""
        response = await async_client.post("/api/queues/emails/pause")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["queue_name"] == "emails"
        assert data["action"] == "pause"
        assert "paused successfully" in data["message"]

    async def test_pause_queue_with_reason(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test pausing a queue with a reason."""
        response = await async_client.post(
            "/api/queues/emails/pause",
            json={"reason": "Maintenance window"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Maintenance window" in data["message"]

    async def test_pause_already_paused_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that pausing an already paused queue fails."""
        response = await async_client.post("/api/queues/payments/pause")
        assert response.status_code == 400

        data = response.json()
        assert "already paused" in data["detail"].lower()

    async def test_pause_nonexistent_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that pausing a non-existent queue fails with 404."""
        response = await async_client.post("/api/queues/nonexistent/pause")
        assert response.status_code == 404


class TestResumeQueue:
    """Tests for POST /api/queues/{name}/resume endpoint."""

    async def test_resume_paused_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test resuming a paused queue."""
        response = await async_client.post("/api/queues/payments/resume")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["queue_name"] == "payments"
        assert data["action"] == "resume"
        assert "resumed successfully" in data["message"]

    async def test_resume_non_paused_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that resuming a non-paused queue fails."""
        response = await async_client.post("/api/queues/emails/resume")
        assert response.status_code == 400

        data = response.json()
        assert "not paused" in data["detail"].lower()

    async def test_resume_nonexistent_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that resuming a non-existent queue fails with 404."""
        response = await async_client.post("/api/queues/nonexistent/resume")
        assert response.status_code == 404


class TestClearQueue:
    """Tests for DELETE /api/queues/{name} endpoint."""

    async def test_clear_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test clearing all pending tasks from a queue."""
        response = await async_client.delete("/api/queues/emails")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["queue_name"] == "emails"
        assert data["tasks_cleared"] == 42  # Original depth of emails queue
        assert "Cleared" in data["message"]

    async def test_clear_empty_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test clearing an empty queue returns 0 tasks cleared."""
        # First clear the queue
        await async_client.delete("/api/queues/emails")

        # Try to clear again
        response = await async_client.delete("/api/queues/emails")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["tasks_cleared"] == 0

    async def test_clear_nonexistent_queue(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that clearing a non-existent queue fails with 404."""
        response = await async_client.delete("/api/queues/nonexistent")
        assert response.status_code == 404


# ============================================================================
# Tests: Alert Levels
# ============================================================================


class TestQueueAlertLevels:
    """Tests for queue alert level calculations."""

    async def test_normal_alert_level(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test queue with depth < 100 has normal alert level."""
        response = await async_client.get("/api/queues/emails")
        assert response.status_code == 200

        data = response.json()
        assert data["depth"] == 42
        assert data["alert_level"] == "normal"

    async def test_warning_alert_level(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test queue with depth >= 100 has warning alert level."""
        response = await async_client.get("/api/queues/reports")
        assert response.status_code == 200

        data = response.json()
        assert data["depth"] == 150
        assert data["alert_level"] == "warning"

    async def test_critical_alert_level(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test queue with depth >= 500 has critical alert level."""
        response = await async_client.get("/api/queues/notifications")
        assert response.status_code == 200

        data = response.json()
        assert data["depth"] == 550
        assert data["alert_level"] == "critical"


# ============================================================================
# Tests: Computed Fields
# ============================================================================


class TestQueueComputedFields:
    """Tests for queue computed field calculations."""

    async def test_total_tasks_computed(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test total_tasks includes pending + processing + completed + failed."""
        response = await async_client.get("/api/queues/emails")
        assert response.status_code == 200

        data = response.json()
        expected_total = (
            data["depth"] + data["processing"] + data["completed_total"] + data["failed_total"]
        )
        assert data["total_tasks"] == expected_total

    async def test_success_rate_computed(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test success_rate is calculated correctly."""
        response = await async_client.get("/api/queues/emails")
        assert response.status_code == 200

        data = response.json()
        completed = data["completed_total"]
        failed = data["failed_total"]
        expected_rate = (completed / (completed + failed)) * 100
        assert abs(data["success_rate"] - expected_rate) < 0.01

    async def test_is_idle_computed(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test is_idle is true when depth and processing are 0."""
        # First clear queue and check
        await async_client.delete("/api/queues/emails")

        response = await async_client.get("/api/queues/emails")
        assert response.status_code == 200

        data = response.json()
        # After clearing, depth is 0 but processing may still be > 0
        if data["depth"] == 0 and data["processing"] == 0:
            assert data["is_idle"] is True
        else:
            assert data["is_idle"] is False
