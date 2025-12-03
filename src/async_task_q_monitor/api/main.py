"""FastAPI app factory for the monitor application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from async_task_q_monitor.services.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

# Path to the static frontend assets (bundled with the package)
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage startup and shutdown events for the monitoring app."""
    logger.info("Starting async-task-q-monitor...")

    # Initialize a metrics collector if available. Import is absolute to
    # satisfy linters and type checkers. If the collector creation fails
    # with ImportError we continue without it.
    try:
        collector = MetricsCollector()
        await collector.start()
        app.state.metrics_collector = collector
    except ImportError:
        logger.debug("MetricsCollector not available; continuing without it")

    yield

    collector = getattr(app.state, "metrics_collector", None)
    if collector is not None:
        try:
            await collector.stop()
        except Exception as exc:  # pragma: no cover - best-effort shutdown  # noqa: BLE001
            logger.debug("Error shutting down metrics collector: %s", exc)


def create_monitoring_app(
    *,
    _enable_auth: bool = True,
    cors_origins: list[str] | None = None,
    _database_url: str | None = None,
) -> FastAPI:
    """Create and configure the monitoring FastAPI app.

    This function performs lazy imports for route modules to avoid
    import-time dependencies during packaging and tests.
    """
    app = FastAPI(
        title="Async Task Q Monitor",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers; import explicitly using absolute imports.
    try:
        # local import to avoid import-time dependency on optional modules
        from async_task_q_monitor.api.routes import (  # noqa: PLC0415
            dashboard,
            metrics,
            queues,
            tasks,
            websocket,
            workers,
        )

        app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
        app.include_router(tasks.router, prefix="/api", tags=["tasks"])
        app.include_router(workers.router, prefix="/api", tags=["workers"])
        app.include_router(queues.router, prefix="/api", tags=["queues"])
        app.include_router(metrics.router, prefix="/api", tags=["metrics"])
        app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
    except Exception as exc:  # noqa: BLE001 - optional modules may be missing
        logger.debug("One or more route modules not available; continuing: %s", exc)

    # Mount static frontend assets if available (bundled with package)
    _mount_static_frontend(app)

    return app


def _mount_static_frontend(app: FastAPI) -> None:
    """Mount the static frontend SPA if the static directory exists.

    The frontend is built by Vite and output to src/async_task_q_monitor/static/
    during the package build process. This function mounts those assets and
    sets up a catch-all route to serve the SPA for client-side routing.
    """
    if not STATIC_DIR.exists():
        logger.debug("Static directory not found at %s; frontend not available", STATIC_DIR)
        return

    index_html = STATIC_DIR / "index.html"
    if not index_html.exists():
        logger.debug("index.html not found in static directory; frontend not available")
        return

    # Mount the assets directory for JS/CSS bundles
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info("Mounted frontend assets from %s", assets_dir)

    # Serve favicon and other static files from root
    for static_file in ["favicon.ico", "favicon.svg", "robots.txt"]:
        static_path = STATIC_DIR / static_file
        if static_path.exists():

            @app.get(f"/{static_file}", include_in_schema=False)
            async def serve_static_file(path: Path = static_path) -> FileResponse:
                return FileResponse(path)

    # Catch-all route for SPA client-side routing
    # This must be registered last to not interfere with API routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve the SPA index.html for all non-API routes."""
        # Don't serve SPA for API or WebSocket routes
        if full_path.startswith(("api/", "ws/", "docs", "redoc", "openapi.json")):
            # Let FastAPI handle these normally (will 404 if not found)
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index_html)

    logger.info("Frontend SPA mounted from %s", STATIC_DIR)
