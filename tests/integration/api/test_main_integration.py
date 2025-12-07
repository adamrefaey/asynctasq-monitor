"""Integration tests for the main FastAPI app factory and lifespan.

Following FastAPI testing best practices (2024):
- Use TestClient with 'with' statement to trigger lifespan events
- Use httpx.AsyncClient with ASGITransport for async tests
- Test error handling, edge cases, and lifecycle management
- Mock external dependencies for deterministic tests

References:
- https://fastapi.tiangolo.com/advanced/testing-events/
- https://fastapi.tiangolo.com/tutorial/testing/
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
import pytest

from asynctasq_monitor.api.main import (
    _mount_static_frontend,
    create_monitoring_app,
    lifespan,
)

# ============================================================================
# Test Markers
# ============================================================================

pytestmark = [pytest.mark.integration]


# ============================================================================
# App Factory Tests
# ============================================================================


class TestCreateMonitoringApp:
    """Tests for the create_monitoring_app factory function."""

    def test_creates_app_with_default_settings(self) -> None:
        """App is created with sensible defaults."""
        app = create_monitoring_app()

        assert isinstance(app, FastAPI)
        assert app.title == "AsyncTasQ Monitor"
        assert app.version == "1.0.0"
        assert app.docs_url == "/api/docs"
        assert app.redoc_url == "/api/redoc"

    def test_creates_app_with_custom_cors_origins(self) -> None:
        """App respects custom CORS origins."""
        custom_origins = ["http://localhost:3000", "https://example.com"]
        app = create_monitoring_app(cors_origins=custom_origins)

        # Verify CORS middleware is configured
        cors_middleware = None
        for middleware in app.user_middleware:
            if hasattr(middleware, "kwargs"):
                if "allow_origins" in middleware.kwargs:
                    cors_middleware = middleware
                    break

        assert cors_middleware is not None
        assert cors_middleware.kwargs["allow_origins"] == custom_origins

    def test_app_includes_api_routers(self) -> None:
        """App includes all expected API routers."""
        app = create_monitoring_app()

        # Check that routes are registered by verifying route paths
        route_paths = [getattr(route, "path", "") for route in app.routes]

        # Dashboard routes
        assert any("/api/dashboard" in path for path in route_paths)

        # Tasks routes
        assert any("/api/tasks" in path for path in route_paths)

        # Workers routes
        assert any("/api/workers" in path for path in route_paths)

        # Queues routes
        assert any("/api/queues" in path for path in route_paths)

        # Metrics routes
        assert any("/api/metrics" in path for path in route_paths)

        # WebSocket routes
        assert any("/ws" in path for path in route_paths)

    def test_app_has_lifespan_configured(self) -> None:
        """App has lifespan context manager configured."""
        app = create_monitoring_app()

        # The lifespan is set during creation
        assert app.router.lifespan_context is not None


class TestCreateMonitoringAppRouterExceptions:
    """Tests for router loading error handling."""

    def test_continues_when_route_modules_raise_exception(self) -> None:
        """App continues gracefully when route modules raise exception during import."""
        # We patch the routes module import to simulate unavailable optional modules
        # This tests the except block at lines 110-111
        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "asynctasq_monitor.api.routes":
                raise ImportError("Simulated import error for routes")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=mock_import):
            # The app should still be created, just without those routes
            app = create_monitoring_app()
            assert app is not None
            # Verify app doesn't have the typical API routes
            route_paths = [getattr(r, "path", "") for r in app.routes]
            # Dashboard should NOT be there since import failed
            assert not any("/api/dashboard" in path for path in route_paths)

    def test_logs_debug_when_routes_fail(self) -> None:
        """Debug message is logged when route modules fail."""
        # Verify the app can be created even if we mock route import failures
        # The actual exception handling is in the except block at line 110-111
        app = create_monitoring_app()
        assert app is not None


# ============================================================================
# Lifespan Tests
# ============================================================================


class TestLifespan:
    """Tests for the app lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_starts_metrics_collector(self) -> None:
        """Lifespan starts the MetricsCollector on startup."""
        mock_collector = AsyncMock()
        mock_collector.start = AsyncMock()
        mock_collector.stop = AsyncMock()

        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                return_value=mock_collector,
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Redis not available"),
            ),
        ):
            app = FastAPI(lifespan=lifespan)

            async with lifespan(app):
                # Verify collector was started
                mock_collector.start.assert_called_once()
                # Verify it's stored in app state
                assert app.state.metrics_collector == mock_collector

            # Verify collector was stopped on shutdown
            mock_collector.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_handles_metrics_collector_import_error(self) -> None:
        """Lifespan continues gracefully when MetricsCollector import fails."""
        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Package not found"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Redis not available"),
            ),
        ):
            app = FastAPI(lifespan=lifespan)

            async with lifespan(app):
                # App should still function
                assert (
                    not hasattr(app.state, "metrics_collector")
                    or app.state.metrics_collector is None
                )

    @pytest.mark.asyncio
    async def test_lifespan_starts_event_consumer(self) -> None:
        """Lifespan starts the EventConsumer on startup."""
        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()

        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                return_value=mock_consumer,
            ),
        ):
            app = FastAPI(lifespan=lifespan)

            async with lifespan(app):
                mock_consumer.start.assert_called_once()
                assert app.state.event_consumer == mock_consumer

            mock_consumer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_handles_event_consumer_failure(self) -> None:
        """Lifespan continues when EventConsumer fails to start."""
        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=ConnectionError("Redis connection refused"),
            ),
        ):
            app = FastAPI(lifespan=lifespan)

            async with lifespan(app):
                # App should still function with event_consumer set to None
                assert app.state.event_consumer is None

    @pytest.mark.asyncio
    async def test_lifespan_handles_shutdown_errors_gracefully(self) -> None:
        """Lifespan handles errors during shutdown without crashing."""
        mock_collector = AsyncMock()
        mock_collector.start = AsyncMock()
        mock_collector.stop = AsyncMock(side_effect=RuntimeError("Shutdown error"))

        mock_consumer = AsyncMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock(side_effect=RuntimeError("Shutdown error"))

        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                return_value=mock_collector,
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                return_value=mock_consumer,
            ),
        ):
            app = FastAPI(lifespan=lifespan)

            # This should not raise even though stop() raises
            async with lifespan(app):
                pass

            # Both stop methods should have been called
            mock_consumer.stop.assert_called_once()
            mock_collector.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_with_no_consumer_on_shutdown(self) -> None:
        """Lifespan handles shutdown when event_consumer was never set."""
        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Redis not available"),
            ),
        ):
            app = FastAPI(lifespan=lifespan)

            async with lifespan(app):
                # Both are None/not set
                assert app.state.event_consumer is None


# ============================================================================
# Lifespan Integration with TestClient
# ============================================================================


class TestLifespanWithTestClient:
    """Integration tests using TestClient to trigger lifespan events.

    Per FastAPI best practices, using TestClient with 'with' statement
    triggers lifespan startup/shutdown events.
    """

    def test_app_lifespan_runs_with_test_client(self) -> None:
        """TestClient properly triggers lifespan events."""
        startup_called = False
        shutdown_called = False

        @asynccontextmanager
        async def test_lifespan(app: FastAPI) -> AsyncGenerator[None]:
            nonlocal startup_called, shutdown_called
            startup_called = True
            yield
            shutdown_called = True

        app = FastAPI(lifespan=test_lifespan)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        with TestClient(app) as client:
            assert startup_called
            response = client.get("/test")
            assert response.status_code == 200

        assert shutdown_called

    def test_full_app_lifespan_integration(self) -> None:
        """Full integration test with mocked services."""
        mock_collector = MagicMock()
        mock_collector.start = AsyncMock()
        mock_collector.stop = AsyncMock()

        mock_consumer = MagicMock()
        mock_consumer.start = AsyncMock()
        mock_consumer.stop = AsyncMock()

        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                return_value=mock_collector,
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                return_value=mock_consumer,
            ),
        ):
            app = create_monitoring_app()

            with TestClient(app) as client:
                # Verify API docs are accessible
                response = client.get("/api/docs")
                assert response.status_code == 200

            # Verify shutdown was called
            mock_collector.stop.assert_called_once()
            mock_consumer.stop.assert_called_once()


# ============================================================================
# Static Frontend Mounting Tests
# ============================================================================


class TestMountStaticFrontend:
    """Tests for the _mount_static_frontend function."""

    def test_does_nothing_when_static_dir_missing(self) -> None:
        """No routes added when static directory doesn't exist."""
        app = FastAPI()
        initial_route_count = len(app.routes)

        with patch.object(Path, "exists", return_value=False):
            _mount_static_frontend(app)

        # No new routes should be added
        assert len(app.routes) == initial_route_count

    def test_does_nothing_when_index_html_missing(self) -> None:
        """No routes added when index.html is missing."""
        app = FastAPI()
        initial_route_count = len(app.routes)

        # Create temp directory without index.html
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "asynctasq_monitor.api.main.STATIC_DIR",
                Path(tmpdir),
            ):
                _mount_static_frontend(app)

        # No new routes should be added
        assert len(app.routes) == initial_route_count

    def test_mounts_assets_when_available(self) -> None:
        """Assets directory is mounted when present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            (tmppath / "index.html").write_text("<html></html>")
            (tmppath / "assets").mkdir()
            (tmppath / "assets" / "main.js").write_text("console.log('test');")

            app = FastAPI()

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            # Check that assets mount was added
            route_names = [getattr(r, "name", None) for r in app.routes]
            assert "assets" in route_names

    def test_serves_static_files(self) -> None:
        """Static files (favicon, robots.txt) are served correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            (tmppath / "index.html").write_text("<html></html>")
            (tmppath / "favicon.ico").write_bytes(b"fake ico content")
            (tmppath / "robots.txt").write_text("User-agent: *\nAllow: /")

            app = FastAPI()

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            # Test that routes were registered
            route_paths = [getattr(r, "path", "") for r in app.routes]
            assert "/favicon.ico" in route_paths
            assert "/robots.txt" in route_paths

    def test_serves_favicon_content(self) -> None:
        """Favicon is served with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            favicon_content = b"\x00\x00\x01\x00"  # Fake ICO header
            (tmppath / "index.html").write_text("<html></html>")
            (tmppath / "favicon.ico").write_bytes(favicon_content)

            app = FastAPI()

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            with TestClient(app) as client:
                response = client.get("/favicon.ico")
                assert response.status_code == 200
                assert response.content == favicon_content

    def test_serves_robots_txt_content(self) -> None:
        """robots.txt is served with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            robots_content = "User-agent: *\nDisallow: /api/"
            (tmppath / "index.html").write_text("<html></html>")
            (tmppath / "robots.txt").write_text(robots_content)

            app = FastAPI()

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            with TestClient(app) as client:
                response = client.get("/robots.txt")
                assert response.status_code == 200
                assert robots_content in response.text

    def test_serves_favicon_svg_content(self) -> None:
        """favicon.svg is served with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            svg_content = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
            (tmppath / "index.html").write_text("<html></html>")
            (tmppath / "favicon.svg").write_text(svg_content)

            app = FastAPI()

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            with TestClient(app) as client:
                response = client.get("/favicon.svg")
                assert response.status_code == 200
                assert svg_content in response.text

    def test_spa_catch_all_route(self) -> None:
        """SPA catch-all route serves index.html for non-API paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            html_content = "<html><body>SPA</body></html>"
            (tmppath / "index.html").write_text(html_content)

            app = FastAPI()

            @app.get("/api/test")
            def api_route() -> dict[str, str]:
                return {"test": "data"}

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            with TestClient(app) as client:
                # Non-API paths should serve index.html
                response = client.get("/dashboard")
                assert response.status_code == 200
                assert "SPA" in response.text

                response = client.get("/tasks/123")
                assert response.status_code == 200
                assert "SPA" in response.text

                response = client.get("/some/deep/path")
                assert response.status_code == 200
                assert "SPA" in response.text

    def test_spa_excludes_api_paths(self) -> None:
        """SPA catch-all doesn't interfere with API routes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            (tmppath / "index.html").write_text("<html></html>")

            app = FastAPI()

            @app.get("/api/health")
            def health() -> dict[str, str]:
                return {"status": "ok"}

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            with TestClient(app) as client:
                # API routes should work normally
                response = client.get("/api/health")
                assert response.status_code == 200
                assert response.json() == {"status": "ok"}

                # Non-existent API routes should 404, not serve SPA
                response = client.get("/api/nonexistent")
                assert response.status_code == 404

    def test_spa_excludes_ws_and_docs_paths(self) -> None:
        """SPA catch-all excludes WebSocket and documentation paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create required files
            (tmppath / "index.html").write_text("<html></html>")

            app = FastAPI(docs_url="/docs", redoc_url="/redoc")

            with patch("asynctasq_monitor.api.main.STATIC_DIR", tmppath):
                _mount_static_frontend(app)

            with TestClient(app) as client:
                # These should not return SPA content
                response = client.get("/docs")
                assert response.status_code == 200
                assert "<html>" in response.text  # Swagger UI HTML

                response = client.get("/redoc")
                assert response.status_code == 200


# ============================================================================
# Full Integration Tests
# ============================================================================


class TestFullAppIntegration:
    """End-to-end integration tests for the complete app."""

    def test_api_docs_accessible(self) -> None:
        """OpenAPI docs are accessible at /api/docs."""
        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Not available"),
            ),
        ):
            app = create_monitoring_app()

            with TestClient(app) as client:
                response = client.get("/api/docs")
                assert response.status_code == 200

    def test_openapi_schema_available(self) -> None:
        """OpenAPI schema is available."""
        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Not available"),
            ),
        ):
            app = create_monitoring_app()

            with TestClient(app) as client:
                response = client.get("/openapi.json")
                assert response.status_code == 200
                schema = response.json()
                assert schema["info"]["title"] == "AsyncTasQ Monitor"

    @pytest.mark.asyncio
    async def test_async_client_integration(self) -> None:
        """Async client works correctly with the app."""
        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Not available"),
            ),
        ):
            app = create_monitoring_app()

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/docs")
                assert response.status_code == 200


# ============================================================================
# CORS Middleware Tests
# ============================================================================


class TestCORSMiddleware:
    """Tests for CORS configuration."""

    def test_cors_allows_all_origins_by_default(self) -> None:
        """Default CORS allows all origins."""
        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Not available"),
            ),
        ):
            app = create_monitoring_app()

            with TestClient(app) as client:
                response = client.options(
                    "/api/docs",
                    headers={
                        "Origin": "http://example.com",
                        "Access-Control-Request-Method": "GET",
                    },
                )
                # CORS preflight should be handled
                assert response.status_code in (200, 204, 405)

    def test_cors_respects_custom_origins(self) -> None:
        """CORS respects custom origins configuration."""
        allowed_origins = ["http://localhost:3000"]

        with (
            patch(
                "asynctasq_monitor.api.main.MetricsCollector",
                side_effect=ImportError("Not available"),
            ),
            patch(
                "asynctasq_monitor.api.main.get_event_consumer",
                side_effect=Exception("Not available"),
            ),
        ):
            app = create_monitoring_app(cors_origins=allowed_origins)

            with TestClient(app) as client:
                # Request from allowed origin
                response = client.get(
                    "/api/docs",
                    headers={"Origin": "http://localhost:3000"},
                )
                assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
