"""FastAPI app factory for the monitor application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from async_task_q_monitor.services.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


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

    # Mount static if available
    try:
        app.mount("/", StaticFiles(directory="static", html=True), name="static")
    except Exception as exc:  # noqa: BLE001 - static mount best-effort
        logger.debug("Static directory not available; skipping mount: %s", exc)

    return app
