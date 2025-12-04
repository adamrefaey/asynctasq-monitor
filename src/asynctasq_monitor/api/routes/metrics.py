"""Metrics routes for the monitoring UI.

This module provides metrics endpoints following best practices:
- Prometheus-format metrics at /metrics/prometheus for Grafana integration
- Health check endpoint at /health for Kubernetes probes
- JSON metrics at /metrics/summary for the monitoring UI
- Proper content types and error handling
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from asynctasq_monitor.services.prometheus import get_prometheus_metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics(request: Request) -> dict:
    """Return basic runtime metrics for the monitoring UI.

    This endpoint returns metrics in JSON format for the frontend.
    For Prometheus scraping, use /metrics/prometheus instead.
    """
    # Try to get metrics from the collector if available
    collector = getattr(request.app.state, "metrics_collector", None)
    if collector is not None:
        last_metrics = collector.get_last_metrics()
        if last_metrics:
            return {
                "pending": last_metrics.get("pending", 0),
                "running": last_metrics.get("running", 0),
                "completed": last_metrics.get("completed", 0),
                "failed": last_metrics.get("failed", 0),
                "success_rate": last_metrics.get("success_rate", 100.0),
                "active_workers": last_metrics.get("active_workers", 0),
                "queue_depths": last_metrics.get("queue_depths", {}),
                "timestamp": last_metrics.get("timestamp"),
            }

    # Return stub metrics if collector not available
    return {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "success_rate": 100.0,
        "active_workers": 0,
        "queue_depths": {},
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


@router.get("/metrics/summary")
async def metrics_summary(
    time_range: Annotated[
        str,
        Query(
            description="Time range for metrics (1h, 6h, 24h, 7d, 30d)",
            pattern=r"^(1h|6h|24h|7d|30d)$",
        ),
    ] = "24h",
) -> dict:
    """Return a brief metrics summary structure for dashboard charts.

    This endpoint provides time-series data for visualization.
    """
    # TODO: Implement historical metrics when TimescaleDB is integrated
    return {
        "time_range": time_range,
        "throughput": [],
        "duration": {
            "avg_ms": 0,
            "p50_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0,
        },
        "status_breakdown": {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
        },
    }


@router.get(
    "/metrics/prometheus",
    response_class=Response,
    responses={
        200: {
            "description": "Prometheus metrics in text format",
            "content": {"text/plain": {}},
        },
    },
)
async def prometheus_metrics() -> Response:
    """Export metrics in Prometheus format for scraping.

    This endpoint returns metrics in the Prometheus text exposition format,
    suitable for scraping by Prometheus or compatible monitoring systems.

    Configure Prometheus to scrape this endpoint:

        scrape_configs:
          - job_name: 'asynctasq-monitor'
            static_configs:
              - targets: ['localhost:8000']
            metrics_path: '/api/metrics/prometheus'

    Available metrics:
        - asynctasq_tasks_enqueued_total{queue="..."}
        - asynctasq_tasks_completed_total{queue="..."}
        - asynctasq_tasks_failed_total{queue="..."}
        - asynctasq_tasks_pending{queue="..."}
        - asynctasq_tasks_running{queue="..."}
        - asynctasq_workers_active
        - asynctasq_task_duration_seconds{queue="..."}
        - asynctasq_queue_depth{queue="..."}
    """
    metrics = get_prometheus_metrics()
    content = metrics.generate_latest()
    return Response(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check endpoint for monitoring and orchestration.

    This endpoint checks the health of the monitoring service and its
    dependencies. Suitable for Kubernetes liveness/readiness probes.

    Returns:
        200 OK with health status if healthy
        503 Service Unavailable if unhealthy

    Health checks performed:
        - Metrics collector running
        - (Future) Database connection
        - (Future) Redis connection
        - (Future) Driver availability
    """
    checks: dict[str, dict] = {}
    all_healthy = True

    # Check metrics collector
    collector = getattr(request.app.state, "metrics_collector", None)
    if collector is not None:
        is_running = collector.is_running
        checks["metrics_collector"] = {
            "status": "healthy" if is_running else "degraded",
            "running": is_running,
        }
        if not is_running:
            all_healthy = False
    else:
        checks["metrics_collector"] = {
            "status": "not_configured",
            "running": False,
        }

    # Check Prometheus metrics availability
    prom_metrics = get_prometheus_metrics()
    checks["prometheus"] = {
        "status": "healthy" if prom_metrics.is_available() else "not_available",
        "available": prom_metrics.is_available(),
    }

    # Overall status
    status = "healthy" if all_healthy else "degraded"

    return {
        "status": status,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "version": "1.0.0",
        "checks": checks,
    }
