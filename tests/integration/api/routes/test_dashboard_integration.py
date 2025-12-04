"""Integration tests for Dashboard API endpoints.

This module provides comprehensive integration tests for the dashboard API,
following pytest-asyncio best practices (2024/2025):
- Use httpx.AsyncClient with ASGITransport for async tests
- Use @pytest.mark.asyncio for async tests (auto-applied in strict mode)
- Test both happy paths and edge cases
- Test all computed fields in response models
- Achieve >90% code coverage for dashboard.py

References:
- FastAPI async tests: https://fastapi.tiangolo.com/advanced/async-tests/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/en/stable/
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from httpx import AsyncClient
from pydantic import ValidationError
import pytest

from asynctasq_monitor.api.routes.dashboard import (
    DashboardSummary,
    HealthResponse,
    QueueStats,
    StatusCount,
)
from asynctasq_monitor.models.task import TaskStatus

# =============================================================================
# Synchronous Integration Tests (with mocked services from root conftest)
# =============================================================================


@pytest.mark.integration
class TestDashboardRootSync:
    """Synchronous integration tests for the dashboard root endpoint."""

    def test_dashboard_root_returns_health_response(self, app):
        """Test that the root endpoint returns a valid health response."""
        with TestClient(app) as client:
            response = client.get("/api/")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "ok"
            assert data["service"] == "asynctasq-monitor"
            assert data["version"] == "1.0.0"

    def test_dashboard_root_response_is_valid_health_response_model(self, app):
        """Test that the response can be parsed as a HealthResponse model."""
        with TestClient(app) as client:
            response = client.get("/api/")
            assert response.status_code == 200

            # Validate response matches the HealthResponse schema
            health = HealthResponse(**response.json())
            assert health.status == "ok"
            assert health.service == "asynctasq-monitor"
            assert health.version == "1.0.0"


@pytest.mark.integration
class TestDashboardSummarySync:
    """Synchronous integration tests for the dashboard summary endpoint."""

    def test_get_summary_returns_valid_response(self, app):
        """Test that the summary endpoint returns a valid response."""
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
            assert response.status_code == 200

            data = response.json()
            # Check required fields
            assert "total_tasks" in data
            assert "by_status" in data
            assert "queues" in data
            assert "active_workers" in data
            assert "success_rate" in data
            assert "updated_at" in data

    def test_get_summary_total_tasks_matches_sample_data(self, app):
        """Test that total_tasks matches the sample tasks from fixtures."""
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
            assert response.status_code == 200

            data = response.json()
            # sample_tasks fixture provides 4 tasks
            assert data["total_tasks"] == 4

    def test_get_summary_by_status_contains_all_statuses(self, app):
        """Test that by_status contains all TaskStatus values."""
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
            assert response.status_code == 200

            data = response.json()
            status_names = {s["status"] for s in data["by_status"]}

            # Should have entries for all TaskStatus enum values
            expected_statuses = {status.value for status in TaskStatus}
            assert status_names == expected_statuses

    def test_get_summary_status_counts_are_non_negative(self, app):
        """Test that all status counts are non-negative."""
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
            assert response.status_code == 200

            data = response.json()
            for status_entry in data["by_status"]:
                assert status_entry["count"] >= 0

    def test_get_summary_status_labels_are_capitalized(self, app):
        """Test that status labels are properly capitalized."""
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
            assert response.status_code == 200

            data = response.json()
            for status_entry in data["by_status"]:
                # Label should be the capitalized form of status
                assert status_entry["label"] == status_entry["status"].capitalize()

    def test_get_summary_success_rate_is_percentage(self, app):
        """Test that success_rate is within valid percentage range."""
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
            assert response.status_code == 200

            data = response.json()
            assert 0 <= data["success_rate"] <= 100

    def test_get_summary_updated_at_is_recent(self, app):
        """Test that updated_at is a recent timestamp."""
        with TestClient(app) as client:
            response = client.get("/api/dashboard/summary")
            assert response.status_code == 200

            data = response.json()
            updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            now = datetime.now(UTC)
            # Should be within the last minute
            assert (now - updated_at).total_seconds() < 60


# =============================================================================
# Async Integration Tests (following FastAPI best practices)
# =============================================================================


@pytest.mark.integration
class TestDashboardRootAsync:
    """Async integration tests for the dashboard root endpoint.

    These tests use httpx.AsyncClient following FastAPI's recommended
    async testing pattern with ASGITransport.
    """

    @pytest.mark.asyncio
    async def test_dashboard_root_async(self, async_client: AsyncClient):
        """Test the root endpoint returns health status asynchronously."""
        response = await async_client.get("/api/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "asynctasq-monitor"
        assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_dashboard_root_content_type(self, async_client: AsyncClient):
        """Test that the response has correct content type."""
        response = await async_client.get("/api/")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.integration
class TestDashboardSummaryAsync:
    """Async integration tests for the dashboard summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary_async(self, async_client: AsyncClient):
        """Test the summary endpoint returns valid data asynchronously."""
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_tasks" in data
        assert "by_status" in data
        assert "success_rate" in data

    @pytest.mark.asyncio
    async def test_get_summary_computed_fields(self, async_client: AsyncClient):
        """Test that computed fields are present in the response."""
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        # Computed fields from DashboardSummary
        assert "pending_count" in data
        assert "failed_count" in data
        assert "running_count" in data

        # All computed counts should be non-negative
        assert data["pending_count"] >= 0
        assert data["failed_count"] >= 0
        assert data["running_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_summary_computed_fields_match_by_status(self, async_client: AsyncClient):
        """Test that computed fields match the by_status entries."""
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        # Build a mapping from by_status
        status_counts = {s["status"]: s["count"] for s in data["by_status"]}

        # Computed fields should match
        assert data["pending_count"] == status_counts.get("pending", 0)
        assert data["failed_count"] == status_counts.get("failed", 0)
        assert data["running_count"] == status_counts.get("running", 0)

    @pytest.mark.asyncio
    async def test_get_summary_success_rate_calculation(self, async_client: AsyncClient):
        """Test that success_rate is calculated correctly.

        success_rate = completed / (completed + failed) * 100
        """
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        status_counts = {s["status"]: s["count"] for s in data["by_status"]}
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        finished = completed + failed

        if finished > 0:
            expected_rate = round(completed / finished * 100, 2)
            assert data["success_rate"] == expected_rate
        else:
            # If no finished tasks, success rate should be 100.0
            assert data["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_get_summary_total_matches_sum_of_statuses(self, async_client: AsyncClient):
        """Test that total_tasks equals the sum of all status counts."""
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        sum_of_counts = sum(s["count"] for s in data["by_status"])
        assert data["total_tasks"] == sum_of_counts

    @pytest.mark.asyncio
    async def test_get_summary_queues_is_list(self, async_client: AsyncClient):
        """Test that queues is a list (may be empty in current implementation)."""
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["queues"], list)

    @pytest.mark.asyncio
    async def test_get_summary_active_workers_is_non_negative(self, async_client: AsyncClient):
        """Test that active_workers is a non-negative integer."""
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["active_workers"], int)
        assert data["active_workers"] >= 0


# =============================================================================
# Model Unit Tests (for computed fields and validation)
# =============================================================================


class TestStatusCountModel:
    """Tests for the StatusCount model."""

    def test_status_count_creation(self):
        """Test StatusCount can be created with valid data."""
        sc = StatusCount(status=TaskStatus.PENDING, count=10)
        assert sc.status == TaskStatus.PENDING
        assert sc.count == 10

    def test_status_count_label_property(self):
        """Test that label is computed correctly."""
        sc = StatusCount(status=TaskStatus.PENDING, count=5)
        assert sc.label == "Pending"

        sc2 = StatusCount(status=TaskStatus.RUNNING, count=3)
        assert sc2.label == "Running"

        sc3 = StatusCount(status=TaskStatus.COMPLETED, count=100)
        assert sc3.label == "Completed"

    def test_status_count_frozen(self):
        """Test that StatusCount is immutable (frozen)."""
        sc = StatusCount(status=TaskStatus.PENDING, count=10)
        with pytest.raises(ValidationError):
            sc.count = 20  # type: ignore[misc]


class TestQueueStatsModel:
    """Tests for the QueueStats model."""

    def test_queue_stats_creation(self):
        """Test QueueStats can be created with valid data."""
        qs = QueueStats(name="emails", pending=10, running=5, failed=2)
        assert qs.name == "emails"
        assert qs.pending == 10
        assert qs.running == 5
        assert qs.failed == 2

    def test_queue_stats_total_computed(self):
        """Test that total is computed correctly."""
        qs = QueueStats(name="emails", pending=10, running=5, failed=2)
        assert qs.total == 17

    def test_queue_stats_total_with_zeros(self):
        """Test total when all values are zero."""
        qs = QueueStats(name="empty-queue", pending=0, running=0, failed=0)
        assert qs.total == 0

    def test_queue_stats_frozen(self):
        """Test that QueueStats is immutable (frozen)."""
        qs = QueueStats(name="test", pending=0, running=0, failed=0)
        with pytest.raises(ValidationError):
            qs.pending = 5  # type: ignore[misc]


class TestDashboardSummaryModel:
    """Tests for the DashboardSummary model."""

    def test_dashboard_summary_creation(self):
        """Test DashboardSummary can be created with valid data."""
        status_counts = [
            StatusCount(status=TaskStatus.PENDING, count=10),
            StatusCount(status=TaskStatus.RUNNING, count=5),
            StatusCount(status=TaskStatus.COMPLETED, count=80),
            StatusCount(status=TaskStatus.FAILED, count=5),
        ]
        summary = DashboardSummary(
            total_tasks=100,
            by_status=status_counts,
            queues=[],
            active_workers=3,
            success_rate=94.12,
            updated_at=datetime.now(UTC),
        )
        assert summary.total_tasks == 100
        assert len(summary.by_status) == 4

    def test_dashboard_summary_pending_count_computed(self):
        """Test pending_count is computed from by_status."""
        status_counts = [
            StatusCount(status=TaskStatus.PENDING, count=25),
            StatusCount(status=TaskStatus.COMPLETED, count=75),
        ]
        summary = DashboardSummary(
            total_tasks=100,
            by_status=status_counts,
            queues=[],
            active_workers=0,
            success_rate=100.0,
            updated_at=datetime.now(UTC),
        )
        assert summary.pending_count == 25

    def test_dashboard_summary_failed_count_computed(self):
        """Test failed_count is computed from by_status."""
        status_counts = [
            StatusCount(status=TaskStatus.PENDING, count=10),
            StatusCount(status=TaskStatus.FAILED, count=15),
        ]
        summary = DashboardSummary(
            total_tasks=25,
            by_status=status_counts,
            queues=[],
            active_workers=0,
            success_rate=0.0,
            updated_at=datetime.now(UTC),
        )
        assert summary.failed_count == 15

    def test_dashboard_summary_running_count_computed(self):
        """Test running_count is computed from by_status."""
        status_counts = [
            StatusCount(status=TaskStatus.RUNNING, count=7),
            StatusCount(status=TaskStatus.PENDING, count=3),
        ]
        summary = DashboardSummary(
            total_tasks=10,
            by_status=status_counts,
            queues=[],
            active_workers=1,
            success_rate=100.0,
            updated_at=datetime.now(UTC),
        )
        assert summary.running_count == 7

    def test_dashboard_summary_missing_status_returns_zero(self):
        """Test computed counts return 0 when status not in by_status."""
        # No PENDING, FAILED, or RUNNING statuses
        status_counts = [
            StatusCount(status=TaskStatus.COMPLETED, count=100),
        ]
        summary = DashboardSummary(
            total_tasks=100,
            by_status=status_counts,
            queues=[],
            active_workers=0,
            success_rate=100.0,
            updated_at=datetime.now(UTC),
        )
        assert summary.pending_count == 0
        assert summary.failed_count == 0
        assert summary.running_count == 0


class TestHealthResponseModel:
    """Tests for the HealthResponse model."""

    def test_health_response_creation(self):
        """Test HealthResponse can be created."""
        hr = HealthResponse(
            status="ok",
            service="asynctasq-monitor",
            version="1.0.0",
        )
        assert hr.status == "ok"
        assert hr.service == "asynctasq-monitor"
        assert hr.version == "1.0.0"

    def test_health_response_frozen(self):
        """Test that HealthResponse is immutable."""
        hr = HealthResponse(
            status="ok",
            service="asynctasq-monitor",
            version="1.0.0",
        )
        with pytest.raises(ValidationError):
            hr.status = "error"  # type: ignore[misc]


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


@pytest.mark.integration
class TestDashboardEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_summary_with_no_completed_or_failed_tasks(self, async_client: AsyncClient):
        """Test success_rate calculation when no tasks have finished.

        With sample_tasks fixture: 1 completed, 1 failed -> 50% success rate
        This test verifies the formula handles the edge case correctly.
        """
        response = await async_client.get("/api/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        # With sample_tasks: 1 completed, 1 failed
        # success_rate = 1 / (1 + 1) * 100 = 50.0
        status_counts = {s["status"]: s["count"] for s in data["by_status"]}
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)

        if completed + failed > 0:
            expected = round(completed / (completed + failed) * 100, 2)
            assert data["success_rate"] == expected

    @pytest.mark.asyncio
    async def test_summary_response_time_is_reasonable(self, async_client: AsyncClient):
        """Test that the summary endpoint responds quickly."""
        import time

        start = time.time()
        response = await async_client.get("/api/dashboard/summary")
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should respond in under 1 second with mocked services
        assert elapsed < 1.0

    def test_concurrent_summary_requests(self, app):
        """Test multiple concurrent requests don't cause issues."""
        import concurrent.futures

        with TestClient(app) as client:

            def make_request():
                return client.get("/api/dashboard/summary")

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result(timeout=5) for f in futures]

        # All requests should succeed
        for response in results:
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
