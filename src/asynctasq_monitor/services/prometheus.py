"""Prometheus metrics exporter for asynctasq monitoring.

This module implements Prometheus-format metrics following best practices:
- Use standard metric types (Counter, Gauge, Histogram)
- Include proper labels for multi-dimensional metrics
- Use namespacing for clear metric identification
- Provide both automatic collection and manual update interfaces

The metrics are compatible with Grafana dashboards and Prometheus alerting.

Example Prometheus scrape config:
    scrape_configs:
      - job_name: 'asynctasq'
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/api/metrics/prometheus'
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
    )

logger = logging.getLogger(__name__)


# Namespace for all asynctasq metrics
NAMESPACE = "asynctasq"


class PrometheusMetrics:
    """Prometheus metrics container for asynctasq monitoring.

    This class manages all Prometheus metrics for the monitoring system.
    It lazily initializes metrics to avoid import-time dependencies.

    Usage:
        metrics = PrometheusMetrics()
        metrics.tasks_enqueued.labels(queue="emails").inc()
        metrics.task_duration.labels(queue="emails").observe(1.5)

    Attributes:
        registry: The Prometheus CollectorRegistry for these metrics
    """

    def __init__(self) -> None:
        """Initialize the Prometheus metrics container."""
        self._initialized = False
        self._registry: CollectorRegistry | None = None

        # Metric instances (lazily initialized)
        self._tasks_enqueued: Counter | None = None
        self._tasks_completed: Counter | None = None
        self._tasks_failed: Counter | None = None
        self._tasks_pending: Gauge | None = None
        self._tasks_running: Gauge | None = None
        self._workers_active: Gauge | None = None
        self._task_duration: Histogram | None = None
        self._queue_depth: Gauge | None = None

    def _ensure_initialized(self) -> None:
        """Initialize metrics lazily to handle optional prometheus_client dependency."""
        if self._initialized:
            return

        try:
            from prometheus_client import (
                CollectorRegistry,
                Counter,
                Gauge,
                Histogram,
            )
        except ImportError:
            logger.warning(
                "prometheus_client not installed. Install with: pip install prometheus-client"
            )
            return

        self._registry = CollectorRegistry()

        # Task counters (monotonically increasing)
        self._tasks_enqueued = Counter(
            name="tasks_enqueued_total",
            documentation="Total number of tasks enqueued",
            labelnames=["queue"],
            namespace=NAMESPACE,
            registry=self._registry,
        )

        self._tasks_completed = Counter(
            name="tasks_completed_total",
            documentation="Total number of tasks completed successfully",
            labelnames=["queue"],
            namespace=NAMESPACE,
            registry=self._registry,
        )

        self._tasks_failed = Counter(
            name="tasks_failed_total",
            documentation="Total number of tasks that failed",
            labelnames=["queue"],
            namespace=NAMESPACE,
            registry=self._registry,
        )

        # Task gauges (current values)
        self._tasks_pending = Gauge(
            name="tasks_pending",
            documentation="Number of tasks waiting in queue",
            labelnames=["queue"],
            namespace=NAMESPACE,
            registry=self._registry,
        )

        self._tasks_running = Gauge(
            name="tasks_running",
            documentation="Number of tasks currently being processed",
            labelnames=["queue"],
            namespace=NAMESPACE,
            registry=self._registry,
        )

        # Worker gauge
        self._workers_active = Gauge(
            name="workers_active",
            documentation="Number of active workers",
            namespace=NAMESPACE,
            registry=self._registry,
        )

        # Task duration histogram with sensible buckets for task queues
        # Buckets: 10ms, 50ms, 100ms, 500ms, 1s, 5s, 10s, 30s, 60s, 5min, +Inf
        self._task_duration = Histogram(
            name="task_duration_seconds",
            documentation="Task execution duration in seconds",
            labelnames=["queue"],
            namespace=NAMESPACE,
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, float("inf")),
            registry=self._registry,
        )

        # Queue depth gauge
        self._queue_depth = Gauge(
            name="queue_depth",
            documentation="Current depth (pending tasks) per queue",
            labelnames=["queue"],
            namespace=NAMESPACE,
            registry=self._registry,
        )

        self._initialized = True
        logger.info("Prometheus metrics initialized")

    @property
    def registry(self) -> CollectorRegistry | None:
        """Get the Prometheus CollectorRegistry."""
        self._ensure_initialized()
        return self._registry

    @property
    def tasks_enqueued(self) -> Counter | None:
        """Counter for total tasks enqueued."""
        self._ensure_initialized()
        return self._tasks_enqueued

    @property
    def tasks_completed(self) -> Counter | None:
        """Counter for total tasks completed."""
        self._ensure_initialized()
        return self._tasks_completed

    @property
    def tasks_failed(self) -> Counter | None:
        """Counter for total tasks failed."""
        self._ensure_initialized()
        return self._tasks_failed

    @property
    def tasks_pending(self) -> Gauge | None:
        """Gauge for pending tasks per queue."""
        self._ensure_initialized()
        return self._tasks_pending

    @property
    def tasks_running(self) -> Gauge | None:
        """Gauge for running tasks per queue."""
        self._ensure_initialized()
        return self._tasks_running

    @property
    def workers_active(self) -> Gauge | None:
        """Gauge for active workers."""
        self._ensure_initialized()
        return self._workers_active

    @property
    def task_duration(self) -> Histogram | None:
        """Histogram for task execution duration."""
        self._ensure_initialized()
        return self._task_duration

    @property
    def queue_depth(self) -> Gauge | None:
        """Gauge for queue depth."""
        self._ensure_initialized()
        return self._queue_depth

    def is_available(self) -> bool:
        """Check if Prometheus metrics are available (prometheus_client installed)."""
        self._ensure_initialized()
        return self._registry is not None

    def update_from_collector(
        self,
        pending: int,
        running: int,
        completed: int,
        failed: int,
        active_workers: int,
        queue_depths: dict[str, int],
    ) -> None:
        """Update metrics from the metrics collector.

        This method is called periodically by the MetricsCollector to update
        gauge values with the current state from the task queue driver.

        Args:
            pending: Total pending tasks across all queues
            running: Total running tasks
            completed: Total completed tasks (for counter, but we use as total)
            failed: Total failed tasks (for counter, but we use as total)
            active_workers: Number of active workers
            queue_depths: Dict mapping queue name to depth
        """
        if not self.is_available():
            return

        # Update gauges (these represent current state)
        if self._workers_active is not None:
            self._workers_active.set(active_workers)

        # Update per-queue gauges
        for queue_name, depth in queue_depths.items():
            if self._queue_depth is not None:
                self._queue_depth.labels(queue=queue_name).set(depth)

    def record_task_completed(self, queue: str, duration_seconds: float) -> None:
        """Record a task completion with duration.

        Args:
            queue: Queue name the task belongs to
            duration_seconds: Execution time in seconds
        """
        if not self.is_available():
            return

        if self._tasks_completed is not None:
            self._tasks_completed.labels(queue=queue).inc()

        if self._task_duration is not None:
            self._task_duration.labels(queue=queue).observe(duration_seconds)

    def record_task_failed(self, queue: str) -> None:
        """Record a task failure.

        Args:
            queue: Queue name the task belongs to
        """
        if not self.is_available():
            return

        if self._tasks_failed is not None:
            self._tasks_failed.labels(queue=queue).inc()

    def record_task_enqueued(self, queue: str) -> None:
        """Record a task being enqueued.

        Args:
            queue: Queue name the task was added to
        """
        if not self.is_available():
            return

        if self._tasks_enqueued is not None:
            self._tasks_enqueued.labels(queue=queue).inc()

    def generate_latest(self) -> bytes:
        """Generate the latest metrics in Prometheus text format.

        Returns:
            Metrics in Prometheus exposition format as bytes
        """
        if not self.is_available() or self._registry is None:
            return b"# No metrics available (prometheus_client not installed)\n"

        try:
            from prometheus_client import generate_latest

            return generate_latest(self._registry)
        except ImportError:
            return b"# prometheus_client not available\n"


# Global singleton instance
_prometheus_metrics: PrometheusMetrics | None = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """Get the global PrometheusMetrics singleton.

    Returns:
        The global PrometheusMetrics instance
    """
    global _prometheus_metrics
    if _prometheus_metrics is None:
        _prometheus_metrics = PrometheusMetrics()
    return _prometheus_metrics


def reset_prometheus_metrics() -> None:
    """Reset the global PrometheusMetrics singleton (for testing)."""
    global _prometheus_metrics
    _prometheus_metrics = None
