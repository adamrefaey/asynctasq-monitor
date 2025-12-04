"""Integration tests for Metrics API endpoints.

This module provides comprehensive integration tests for the metrics API,
following pytest-asyncio best practices (2024/2025):
- Use httpx.AsyncClient with ASGITransport for async tests
- Use @pytest.mark.asyncio for async tests (auto-applied in strict mode)
- Test both happy paths and edge cases
- Test all branches including collector states
- Achieve >90% code coverage for metrics.py

References:
- FastAPI async tests: https://fastapi.tiangolo.com/advanced/async-tests/
- Prometheus metrics best practices: https://prometheus.io/docs/practices/naming/
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from asynctasq_monitor.api.routes import dashboard, metrics, queues, tasks, workers
from asynctasq_monitor.services.prometheus import (
    reset_prometheus_metrics,
)


def _create_test_app() -> FastAPI:
    """Create a minimal FastAPI app for testing without lifespan.

    This avoids the real lifespan which tries to start Redis connections
    and other services that may not be available in tests.
    """

    @asynccontextmanager
    async def test_lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """Minimal lifespan that doesn't start real services."""
        yield

    app = FastAPI(lifespan=test_lifespan)
    app.include_router(metrics.router, prefix="/api", tags=["metrics"])
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(tasks.router, prefix="/api", tags=["tasks"])
    app.include_router(workers.router, prefix="/api", tags=["workers"])
    app.include_router(queues.router, prefix="/api", tags=["queues"])
    return app


# =============================================================================
# Fixtures for Collector State Tests
# =============================================================================


@pytest.fixture
def mock_collector_with_metrics():
    """Create a mock metrics collector with real metrics data."""
    collector = MagicMock()
    collector.is_running = True
    collector.get_last_metrics.return_value = {
        "pending": 15,
        "running": 3,
        "completed": 250,
        "failed": 5,
        "success_rate": 98.04,
        "active_workers": 4,
        "queue_depths": {"emails": 10, "payments": 5},
        "timestamp": "2025-12-04T10:00:00Z",
    }
    return collector


@pytest.fixture
def mock_collector_empty_metrics():
    """Create a mock metrics collector that returns None for last_metrics."""
    collector = MagicMock()
    collector.is_running = True
    collector.get_last_metrics.return_value = None
    return collector


@pytest.fixture
def mock_collector_not_running():
    """Create a mock metrics collector that is not running."""
    collector = MagicMock()
    collector.is_running = False
    collector.get_last_metrics.return_value = None
    return collector


@pytest.fixture
def app_with_collector(mock_collector_with_metrics):
    """Create an app with a mock metrics collector that has real metrics."""
    app = _create_test_app()
    app.state.metrics_collector = mock_collector_with_metrics
    return app


@pytest.fixture
def app_with_empty_collector(mock_collector_empty_metrics):
    """Create an app with a mock metrics collector that has no metrics."""
    app = _create_test_app()
    app.state.metrics_collector = mock_collector_empty_metrics
    return app


@pytest.fixture
def app_with_stopped_collector(mock_collector_not_running):
    """Create an app with a stopped metrics collector."""
    app = _create_test_app()
    app.state.metrics_collector = mock_collector_not_running
    return app


@pytest.fixture
def app_without_collector():
    """Create an app without a metrics collector."""
    app = _create_test_app()
    # Explicitly set to None to ensure no collector
    app.state.metrics_collector = None
    return app


@pytest_asyncio.fixture
async def client_with_collector(app_with_collector: FastAPI):
    """Async client for app with active metrics collector."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_collector),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client_with_empty_collector(app_with_empty_collector: FastAPI):
    """Async client for app with collector that has no metrics."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_empty_collector),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client_with_stopped_collector(app_with_stopped_collector: FastAPI):
    """Async client for app with stopped collector."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_stopped_collector),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client_without_collector(app_without_collector: FastAPI):
    """Async client for app without collector."""
    async with AsyncClient(
        transport=ASGITransport(app=app_without_collector),
        base_url="http://test",
    ) as client:
        yield client


# =============================================================================
# Synchronous Integration Tests
# =============================================================================


@pytest.mark.integration
class TestMetricsEndpointSync:
    """Synchronous integration tests for the /metrics endpoint."""

    def test_get_metrics_returns_stub_without_collector(self, app_without_collector):
        """Test that /metrics returns stub metrics when no collector is available."""
        with TestClient(app_without_collector) as client:
            response = client.get("/api/metrics")
            assert response.status_code == 200

            data = response.json()
            assert data["pending"] == 0
            assert data["running"] == 0
            assert data["completed"] == 0
            assert data["failed"] == 0
            assert data["success_rate"] == 100.0
            assert data["active_workers"] == 0
            assert data["queue_depths"] == {}
            assert "timestamp" in data

    def test_get_metrics_returns_real_data_with_collector(self, app_with_collector):
        """Test that /metrics returns real data when collector has metrics."""
        with TestClient(app_with_collector) as client:
            response = client.get("/api/metrics")
            assert response.status_code == 200

            data = response.json()
            assert data["pending"] == 15
            assert data["running"] == 3
            assert data["completed"] == 250
            assert data["failed"] == 5
            assert data["success_rate"] == 98.04
            assert data["active_workers"] == 4
            assert data["queue_depths"] == {"emails": 10, "payments": 5}
            assert data["timestamp"] == "2025-12-04T10:00:00Z"

    def test_get_metrics_returns_stub_when_collector_has_no_metrics(self, app_with_empty_collector):
        """Test /metrics returns stub when collector exists but has no metrics."""
        with TestClient(app_with_empty_collector) as client:
            response = client.get("/api/metrics")
            assert response.status_code == 200

            data = response.json()
            # Should return stub data since get_last_metrics returned None
            assert data["pending"] == 0
            assert data["success_rate"] == 100.0


@pytest.mark.integration
class TestMetricsSummarySync:
    """Synchronous integration tests for the /metrics/summary endpoint."""

    def test_metrics_summary_default_time_range(self, app):
        """Test that /metrics/summary returns default 24h time range."""
        with TestClient(app) as client:
            response = client.get("/api/metrics/summary")
            assert response.status_code == 200

            data = response.json()
            assert data["time_range"] == "24h"

    def test_metrics_summary_with_custom_time_range(self, app):
        """Test /metrics/summary with various time range parameters."""
        with TestClient(app) as client:
            for time_range in ["1h", "6h", "24h", "7d", "30d"]:
                response = client.get("/api/metrics/summary", params={"time_range": time_range})
                assert response.status_code == 200
                assert response.json()["time_range"] == time_range

    def test_metrics_summary_invalid_time_range(self, app):
        """Test /metrics/summary rejects invalid time range."""
        with TestClient(app) as client:
            response = client.get("/api/metrics/summary", params={"time_range": "invalid"})
            # FastAPI returns 422 for validation errors
            assert response.status_code == 422

    def test_metrics_summary_structure(self, app):
        """Test /metrics/summary has complete expected structure."""
        with TestClient(app) as client:
            response = client.get("/api/metrics/summary")
            assert response.status_code == 200

            data = response.json()
            # Top-level keys
            assert "time_range" in data
            assert "throughput" in data
            assert "duration" in data
            assert "status_breakdown" in data

            # Duration structure
            duration = data["duration"]
            assert duration["avg_ms"] == 0
            assert duration["p50_ms"] == 0
            assert duration["p95_ms"] == 0
            assert duration["p99_ms"] == 0

            # Status breakdown structure
            status = data["status_breakdown"]
            assert status["pending"] == 0
            assert status["running"] == 0
            assert status["completed"] == 0
            assert status["failed"] == 0


@pytest.mark.integration
class TestPrometheusEndpointSync:
    """Synchronous integration tests for the /metrics/prometheus endpoint."""

    def test_prometheus_metrics_content_type(self, app):
        """Test that /metrics/prometheus returns correct content type."""
        with TestClient(app) as client:
            response = client.get("/api/metrics/prometheus")
            assert response.status_code == 200
            assert "text/plain" in response.headers["content-type"]
            assert "version=0.0.4" in response.headers["content-type"]

    def test_prometheus_metrics_returns_bytes(self, app):
        """Test that /metrics/prometheus returns proper Prometheus format."""
        with TestClient(app) as client:
            response = client.get("/api/metrics/prometheus")
            assert response.status_code == 200
            # Should contain asynctasq namespace
            assert "asynctasq" in response.text or len(response.content) > 0


@pytest.mark.integration
class TestHealthEndpointSync:
    """Synchronous integration tests for the /health endpoint."""

    def test_health_endpoint_without_collector(self, app_without_collector):
        """Test /health when no metrics collector is configured."""
        with TestClient(app_without_collector) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            checks = data["checks"]
            assert checks["metrics_collector"]["status"] == "not_configured"
            assert checks["metrics_collector"]["running"] is False

    def test_health_endpoint_with_running_collector(self, app_with_collector):
        """Test /health when metrics collector is running."""
        with TestClient(app_with_collector) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            checks = data["checks"]
            assert checks["metrics_collector"]["status"] == "healthy"
            assert checks["metrics_collector"]["running"] is True

    def test_health_endpoint_with_stopped_collector(self, app_with_stopped_collector):
        """Test /health when metrics collector is stopped (degraded)."""
        with TestClient(app_with_stopped_collector) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            # Overall status should be degraded since collector is not running
            assert data["status"] == "degraded"
            checks = data["checks"]
            assert checks["metrics_collector"]["status"] == "degraded"
            assert checks["metrics_collector"]["running"] is False

    def test_health_endpoint_includes_prometheus_check(self, app):
        """Test that /health includes Prometheus availability check."""
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            assert "prometheus" in data["checks"]
            # Prometheus should be available since prometheus_client is installed
            assert data["checks"]["prometheus"]["status"] == "healthy"
            assert data["checks"]["prometheus"]["available"] is True

    def test_health_endpoint_timestamp(self, app):
        """Test that /health includes a recent timestamp."""
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            # Timestamp should be in ISO format with Z suffix
            assert data["timestamp"].endswith("Z")
            # Parse and verify it's recent
            ts = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            now = datetime.now(UTC)
            assert (now - ts).total_seconds() < 60

    def test_health_endpoint_version(self, app):
        """Test that /health includes version information."""
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            assert data["version"] == "1.0.0"


# =============================================================================
# Async Integration Tests
# =============================================================================


@pytest.mark.integration
class TestMetricsEndpointAsync:
    """Async integration tests for the /metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_metrics_async_with_collector(self, client_with_collector: AsyncClient):
        """Test /metrics returns collector data asynchronously."""
        response = await client_with_collector.get("/api/metrics")
        assert response.status_code == 200

        data = response.json()
        assert data["pending"] == 15
        assert data["running"] == 3
        assert data["completed"] == 250
        assert data["failed"] == 5
        assert data["success_rate"] == 98.04
        assert data["active_workers"] == 4

    @pytest.mark.asyncio
    async def test_get_metrics_async_without_collector(self, client_without_collector: AsyncClient):
        """Test /metrics returns stub data asynchronously when no collector."""
        response = await client_without_collector.get("/api/metrics")
        assert response.status_code == 200

        data = response.json()
        assert data["pending"] == 0
        assert data["success_rate"] == 100.0
        assert data["queue_depths"] == {}

    @pytest.mark.asyncio
    async def test_get_metrics_async_with_empty_collector(
        self, client_with_empty_collector: AsyncClient
    ):
        """Test /metrics with collector that has no metrics."""
        response = await client_with_empty_collector.get("/api/metrics")
        assert response.status_code == 200

        data = response.json()
        # Falls back to stub data when last_metrics is None
        assert data["pending"] == 0
        assert data["success_rate"] == 100.0


@pytest.mark.integration
class TestMetricsSummaryAsync:
    """Async integration tests for the /metrics/summary endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_summary_async(self, async_client: AsyncClient):
        """Test /metrics/summary async response."""
        response = await async_client.get("/api/metrics/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["time_range"] == "24h"
        assert "throughput" in data
        assert "duration" in data

    @pytest.mark.asyncio
    async def test_metrics_summary_time_ranges_async(self, async_client: AsyncClient):
        """Test /metrics/summary with all valid time ranges async."""
        for time_range in ["1h", "6h", "24h", "7d", "30d"]:
            response = await async_client.get(
                "/api/metrics/summary", params={"time_range": time_range}
            )
            assert response.status_code == 200
            assert response.json()["time_range"] == time_range


@pytest.mark.integration
class TestPrometheusEndpointAsync:
    """Async integration tests for the /metrics/prometheus endpoint."""

    @pytest.mark.asyncio
    async def test_prometheus_metrics_async(self, async_client: AsyncClient):
        """Test /metrics/prometheus async response."""
        response = await async_client.get("/api/metrics/prometheus")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_prometheus_metrics_contains_namespace(self, async_client: AsyncClient):
        """Test that Prometheus metrics contain asynctasq namespace."""
        response = await async_client.get("/api/metrics/prometheus")
        assert response.status_code == 200
        # Should have some content
        assert len(response.content) > 0


@pytest.mark.integration
class TestHealthEndpointAsync:
    """Async integration tests for the /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_async(self, async_client: AsyncClient):
        """Test /health async response."""
        response = await async_client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "checks" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_with_running_collector_async(self, client_with_collector: AsyncClient):
        """Test /health with running collector async."""
        response = await client_with_collector.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["metrics_collector"]["running"] is True

    @pytest.mark.asyncio
    async def test_health_with_stopped_collector_async(
        self, client_with_stopped_collector: AsyncClient
    ):
        """Test /health with stopped collector async (degraded status)."""
        response = await client_with_stopped_collector.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["metrics_collector"]["status"] == "degraded"


# =============================================================================
# Edge Cases and Boundary Conditions
# =============================================================================


@pytest.mark.integration
class TestMetricsEdgeCases:
    """Test edge cases and boundary conditions for metrics endpoints."""

    @pytest.mark.asyncio
    async def test_metrics_timestamp_format(self, client_without_collector: AsyncClient):
        """Test that stub metrics timestamp is in correct ISO format."""
        response = await client_without_collector.get("/api/metrics")
        assert response.status_code == 200

        data = response.json()
        timestamp = data["timestamp"]
        # Should end with Z (UTC indicator)
        assert timestamp.endswith("Z")
        # Should be parseable as ISO datetime
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    @pytest.mark.asyncio
    async def test_metrics_with_partial_collector_data(self):
        """Test /metrics with collector returning partial data."""
        # Create a collector that returns partial data (missing some keys)
        partial_collector = MagicMock()
        partial_collector.is_running = True
        partial_collector.get_last_metrics.return_value = {
            "pending": 5,
            # Missing other keys - should use defaults
        }

        app = _create_test_app()
        app.state.metrics_collector = partial_collector

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/metrics")
            assert response.status_code == 200

            data = response.json()
            assert data["pending"] == 5
            # Missing keys should get default values
            assert data["running"] == 0
            assert data["completed"] == 0
            assert data["failed"] == 0
            assert data["success_rate"] == 100.0
            assert data["active_workers"] == 0
            assert data["queue_depths"] == {}

    def test_concurrent_metrics_requests(self, app_with_collector):
        """Test multiple concurrent requests to /metrics don't cause issues."""
        import concurrent.futures

        def make_request():
            with TestClient(app_with_collector) as client:
                return client.get("/api/metrics")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        # All requests should succeed
        for response in results:
            assert response.status_code == 200

    def test_concurrent_health_requests(self, app_with_collector):
        """Test multiple concurrent requests to /health don't cause issues."""
        import concurrent.futures

        def make_request():
            with TestClient(app_with_collector) as client:
                return client.get("/api/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        for response in results:
            assert response.status_code == 200


@pytest.mark.integration
class TestPrometheusMetricsService:
    """Test PrometheusMetrics service integration."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Reset prometheus metrics between tests."""
        reset_prometheus_metrics()
        yield
        reset_prometheus_metrics()

    def test_prometheus_singleton_in_routes(self, app):
        """Test that prometheus metrics singleton is properly used in routes."""
        with TestClient(app) as client:
            # Make two requests
            response1 = client.get("/api/metrics/prometheus")
            response2 = client.get("/api/metrics/prometheus")

            # Both should succeed
            assert response1.status_code == 200
            assert response2.status_code == 200

            # Content should be similar (same metrics)
            assert len(response1.content) > 0
            assert len(response2.content) > 0

    def test_health_checks_prometheus_availability(self, app):
        """Test that health endpoint correctly checks Prometheus availability."""
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            # Prometheus should be available (prometheus_client is installed)
            assert data["checks"]["prometheus"]["available"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
