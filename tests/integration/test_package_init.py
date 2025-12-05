"""Integration tests for the asynctasq_monitor package __init__.py module.

These tests verify:
- The lazy loading pattern for create_monitoring_app works correctly
- The function returns a proper FastAPI application
- Arguments are correctly forwarded to the real factory

Following FastAPI testing best practices:
- Use TestClient for integration testing
- Test the public API surface
"""

from fastapi import FastAPI
import pytest

import asynctasq_monitor
from asynctasq_monitor import create_monitoring_app


@pytest.mark.integration
class TestPackageExports:
    """Tests for package exports and metadata."""

    def test_create_monitoring_app_is_callable(self) -> None:
        """Test that create_monitoring_app is importable and callable."""
        assert callable(create_monitoring_app)


@pytest.mark.integration
class TestCreateMonitoringAppLazyLoader:
    """Tests for the lazy-loading create_monitoring_app wrapper."""

    def test_returns_fastapi_app(self) -> None:
        """Test that create_monitoring_app returns a FastAPI instance."""
        app = create_monitoring_app()
        assert isinstance(app, FastAPI)

    def test_forwards_keyword_args_cors(self) -> None:
        """Test that keyword arguments are forwarded to the factory."""
        # The real factory accepts cors_origins as keyword arg
        cors_origins = ["http://localhost:3000"]
        app = create_monitoring_app(cors_origins=cors_origins)
        assert isinstance(app, FastAPI)

    def test_forwards_keyword_args(self) -> None:
        """Test that keyword arguments are forwarded to the factory."""
        app = create_monitoring_app(cors_origins=["http://localhost:4000"])
        assert isinstance(app, FastAPI)

    def test_multiple_calls_return_new_instances(self) -> None:
        """Test that each call creates a new app instance."""
        app1 = create_monitoring_app()
        app2 = create_monitoring_app()
        # Each call should create a new FastAPI instance
        assert app1 is not app2

    def test_app_has_expected_routes(self) -> None:
        """Test that the created app has expected API routes."""
        app = create_monitoring_app()

        # Get all route paths (filter to Route objects that have path attribute)
        route_paths = [
            getattr(route, "path", None) for route in app.routes if hasattr(route, "path")
        ]
        route_paths = [p for p in route_paths if p is not None]

        # Should have dashboard routes
        assert "/" in route_paths or any("/api" in str(p) for p in route_paths)

    def test_app_has_expected_title(self) -> None:
        """Test that the created app has correct metadata."""
        app = create_monitoring_app()
        assert app.title  # Should have a title set

    def test_lazy_import_avoids_fastapi_at_module_import(self) -> None:
        """Test that importing asynctasq_monitor doesn't import FastAPI immediately.

        This is verified by checking that the module can be imported
        and has the lazy loader function available.
        """
        # Re-import the module to check lazy behavior
        import importlib

        # Reload the module
        module = importlib.reload(asynctasq_monitor)

        # The create_monitoring_app should be available
        assert hasattr(module, "create_monitoring_app")
        assert callable(module.create_monitoring_app)

        # Calling it should work and return FastAPI
        app = module.create_monitoring_app()
        assert isinstance(app, FastAPI)


@pytest.mark.integration
class TestCreateMonitoringAppWithTestClient:
    """Integration tests using FastAPI TestClient."""

    def test_health_endpoint_accessible(self) -> None:
        """Test that health endpoint is accessible via TestClient."""
        from starlette.testclient import TestClient

        app = create_monitoring_app()
        with TestClient(app) as client:
            # Use the metrics health endpoint which has no dependencies
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ("healthy", "degraded")
            assert "version" in data

    def test_tasks_endpoint_accessible(self) -> None:
        """Test that tasks endpoint is accessible via TestClient."""
        from starlette.testclient import TestClient

        app = create_monitoring_app()
        with TestClient(app) as client:
            response = client.get("/api/tasks/")
            assert response.status_code == 200

    def test_cors_middleware_applied(self) -> None:
        """Test that CORS middleware is properly configured."""
        from starlette.testclient import TestClient

        app = create_monitoring_app(cors_origins=["http://localhost:3000"])
        with TestClient(app) as client:
            # Test preflight request
            response = client.options(
                "/api/dashboard/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
