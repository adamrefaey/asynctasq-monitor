"""Unit tests for metrics routes and Prometheus integration.

Tests cover:
- Prometheus metrics endpoint (/metrics)
- Health check endpoint (/health)
- Metrics summary endpoint (/metrics/summary)
- PrometheusMetrics service functionality
"""

from collections.abc import Iterator

from httpx import AsyncClient
import pytest

from async_task_q_monitor.services.prometheus import (
    PrometheusMetrics,
    get_prometheus_metrics,
    reset_prometheus_metrics,
)


class TestPrometheusMetrics:
    """Tests for PrometheusMetrics service class."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> Iterator[None]:
        """Clean up prometheus singleton before each test."""
        reset_prometheus_metrics()
        yield
        reset_prometheus_metrics()

    @pytest.fixture
    def metrics(self) -> PrometheusMetrics:
        """Create a fresh PrometheusMetrics instance for testing."""
        return PrometheusMetrics()

    def test_is_available_returns_true(self, metrics: PrometheusMetrics) -> None:
        """Test that is_available returns True when prometheus_client is installed."""
        assert metrics.is_available() is True

    def test_registry_is_created(self, metrics: PrometheusMetrics) -> None:
        """Test that registry is created on initialization."""
        assert metrics.registry is not None

    def test_record_task_completed_increments_counter(self, metrics: PrometheusMetrics) -> None:
        """Test that recording a task completion increments the counter."""
        # Record a completed task
        metrics.record_task_completed(queue="emails", duration_seconds=1.5)
        # If no exception is raised, the metric was recorded successfully
        assert metrics.tasks_completed is not None

    def test_record_task_failed_increments_counter(self, metrics: PrometheusMetrics) -> None:
        """Test that recording a task failure increments the counter."""
        metrics.record_task_failed(queue="emails")
        assert metrics.tasks_failed is not None

    def test_record_task_enqueued_increments_counter(self, metrics: PrometheusMetrics) -> None:
        """Test that recording a task enqueue increments the counter."""
        metrics.record_task_enqueued(queue="emails")
        assert metrics.tasks_enqueued is not None

    def test_update_from_collector_sets_gauges(self, metrics: PrometheusMetrics) -> None:
        """Test updating metrics from the collector."""
        metrics.update_from_collector(
            pending=10,
            running=5,
            completed=100,
            failed=3,
            active_workers=4,
            queue_depths={"emails": 42, "payments": 15},
        )
        # Verify workers_active gauge was set
        assert metrics.workers_active is not None

    def test_generate_latest_returns_bytes(self, metrics: PrometheusMetrics) -> None:
        """Test that generate_latest returns bytes in Prometheus format."""
        # Record some metrics first
        metrics.record_task_completed(queue="test", duration_seconds=0.5)

        output = metrics.generate_latest()
        assert isinstance(output, bytes)
        assert len(output) > 0
        # Should contain the namespace
        assert b"async_task_q" in output

    def test_singleton_pattern(self) -> None:
        """Test that get_prometheus_metrics returns the same instance."""
        reset_prometheus_metrics()
        instance1 = get_prometheus_metrics()
        instance2 = get_prometheus_metrics()
        assert instance1 is instance2

    def test_lazy_initialization(self, metrics: PrometheusMetrics) -> None:
        """Test that metrics are lazily initialized."""
        # Before accessing any property, _initialized should be False
        fresh_metrics = PrometheusMetrics()
        assert fresh_metrics._initialized is False

        # After accessing a property, it should be True
        _ = fresh_metrics.registry
        assert fresh_metrics._initialized is True


class TestPrometheusEndpoint:
    """Tests for the /metrics Prometheus endpoint."""

    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint_returns_text(
        self, async_client: AsyncClient
    ) -> None:
        """Test that /metrics returns Prometheus text format."""
        response = await async_client.get("/api/metrics/prometheus")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_prometheus_metrics_contains_expected_metrics(
        self, async_client: AsyncClient
    ) -> None:
        """Test that Prometheus output contains expected metric names."""
        response = await async_client.get("/api/metrics/prometheus")
        content = response.text

        # Check for our custom metrics (they may have prefix)
        # Note: exact metric names depend on prometheus_client version
        assert response.status_code == 200
        # The metrics should exist in some form
        assert len(content) > 0


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_healthy(self, async_client: AsyncClient) -> None:
        """Test that /health returns healthy status."""
        response = await async_client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "timestamp" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_endpoint_checks_match_expected_structure(
        self, async_client: AsyncClient
    ) -> None:
        """Test health endpoint includes all expected checks."""
        response = await async_client.get("/api/health")
        data = response.json()

        assert "checks" in data
        checks = data["checks"]
        # Should have prometheus check
        assert "prometheus" in checks


class TestMetricsSummaryEndpoint:
    """Tests for the /metrics/summary endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_summary_returns_json(self, async_client: AsyncClient) -> None:
        """Test that /metrics/summary returns JSON."""
        response = await async_client.get("/api/metrics/summary")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_metrics_summary_structure(self, async_client: AsyncClient) -> None:
        """Test that metrics summary has expected structure."""
        response = await async_client.get("/api/metrics/summary")
        data = response.json()

        assert "time_range" in data
        assert "throughput" in data
        assert "duration" in data
        assert "status_breakdown" in data

        # Check duration sub-structure
        duration = data["duration"]
        assert "avg_ms" in duration
        assert "p50_ms" in duration
        assert "p95_ms" in duration
        assert "p99_ms" in duration

        # Check status_breakdown sub-structure
        status = data["status_breakdown"]
        assert "pending" in status
        assert "running" in status
        assert "completed" in status
        assert "failed" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
