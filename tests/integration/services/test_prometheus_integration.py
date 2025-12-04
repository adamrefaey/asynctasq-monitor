"""Integration tests for Prometheus metrics service.

These tests verify:
- PrometheusMetrics class initialization
- All metric properties (counters, gauges, histogram)
- Metric recording methods
- Prometheus format generation
- Singleton pattern for global metrics
- Behavior when prometheus_client is available

Following Prometheus testing best practices:
- Test metric registration and labeling
- Test counter increments and gauge updates
- Test histogram observations
- Test metrics serialization
"""

from collections.abc import Generator

import pytest

from asynctasq_monitor.services.prometheus import (
    NAMESPACE,
    PrometheusMetrics,
    get_prometheus_metrics,
    reset_prometheus_metrics,
)


@pytest.fixture
def prometheus_metrics() -> PrometheusMetrics:
    """Create a fresh PrometheusMetrics instance for testing."""
    return PrometheusMetrics()


@pytest.fixture(autouse=True)
def reset_global_metrics() -> Generator[None]:
    """Reset global metrics singleton before each test."""
    reset_prometheus_metrics()
    yield
    reset_prometheus_metrics()


@pytest.mark.integration
class TestPrometheusMetricsInitialization:
    """Tests for PrometheusMetrics initialization."""

    def test_metrics_not_initialized_at_creation(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that metrics are not initialized until first access."""
        # Check internal state without triggering initialization
        assert prometheus_metrics._initialized is False
        assert prometheus_metrics._registry is None

    def test_lazy_initialization_on_property_access(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that accessing any property triggers initialization."""
        # Access the registry property
        registry = prometheus_metrics.registry

        assert prometheus_metrics._initialized is True
        assert registry is not None

    def test_initialization_only_happens_once(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test that _ensure_initialized only runs once."""
        # Access multiple properties
        _ = prometheus_metrics.registry
        _ = prometheus_metrics.tasks_enqueued
        _ = prometheus_metrics.tasks_completed

        # Should still be the same registry
        assert prometheus_metrics._initialized is True


@pytest.mark.integration
class TestPrometheusMetricsAvailability:
    """Tests for is_available() method."""

    def test_is_available_returns_true_when_prometheus_client_installed(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test is_available returns True when prometheus_client is present."""
        # prometheus_client is installed in dev dependencies
        assert prometheus_metrics.is_available() is True

    def test_is_available_initializes_metrics(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test that is_available triggers initialization."""
        prometheus_metrics.is_available()
        assert prometheus_metrics._initialized is True


@pytest.mark.integration
class TestPrometheusMetricsRegistry:
    """Tests for the metrics registry."""

    def test_registry_property(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test registry property returns a CollectorRegistry."""
        from prometheus_client import CollectorRegistry

        registry = prometheus_metrics.registry
        assert isinstance(registry, CollectorRegistry)


@pytest.mark.integration
class TestPrometheusCounters:
    """Tests for counter metrics."""

    def test_tasks_enqueued_counter(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test tasks_enqueued counter is properly configured."""
        from prometheus_client import Counter

        counter = prometheus_metrics.tasks_enqueued
        assert counter is not None
        assert isinstance(counter, Counter)
        # Check it has the queue label
        assert "queue" in counter._labelnames

    def test_tasks_completed_counter(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test tasks_completed counter is properly configured."""
        from prometheus_client import Counter

        counter = prometheus_metrics.tasks_completed
        assert counter is not None
        assert isinstance(counter, Counter)
        assert "queue" in counter._labelnames

    def test_tasks_failed_counter(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test tasks_failed counter is properly configured."""
        from prometheus_client import Counter

        counter = prometheus_metrics.tasks_failed
        assert counter is not None
        assert isinstance(counter, Counter)
        assert "queue" in counter._labelnames


@pytest.mark.integration
class TestPrometheusGauges:
    """Tests for gauge metrics."""

    def test_tasks_pending_gauge(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test tasks_pending gauge is properly configured."""
        from prometheus_client import Gauge

        gauge = prometheus_metrics.tasks_pending
        assert gauge is not None
        assert isinstance(gauge, Gauge)
        assert "queue" in gauge._labelnames

    def test_tasks_running_gauge(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test tasks_running gauge is properly configured."""
        from prometheus_client import Gauge

        gauge = prometheus_metrics.tasks_running
        assert gauge is not None
        assert isinstance(gauge, Gauge)
        assert "queue" in gauge._labelnames

    def test_workers_active_gauge(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test workers_active gauge is properly configured."""
        from prometheus_client import Gauge

        gauge = prometheus_metrics.workers_active
        assert gauge is not None
        assert isinstance(gauge, Gauge)
        # workers_active has no labels
        assert len(gauge._labelnames) == 0

    def test_queue_depth_gauge(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test queue_depth gauge is properly configured."""
        from prometheus_client import Gauge

        gauge = prometheus_metrics.queue_depth
        assert gauge is not None
        assert isinstance(gauge, Gauge)
        assert "queue" in gauge._labelnames


@pytest.mark.integration
class TestPrometheusHistogram:
    """Tests for histogram metrics."""

    def test_task_duration_histogram(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test task_duration histogram is properly configured."""
        from prometheus_client import Histogram

        histogram = prometheus_metrics.task_duration
        assert histogram is not None
        assert isinstance(histogram, Histogram)
        assert "queue" in histogram._labelnames


@pytest.mark.integration
class TestRecordTaskCompleted:
    """Tests for record_task_completed method."""

    def test_record_task_completed_increments_counter(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that record_task_completed increments the completed counter."""
        # Get initial value
        tasks_completed = prometheus_metrics.tasks_completed
        assert tasks_completed is not None
        initial = tasks_completed.labels(queue="test")._value.get()

        prometheus_metrics.record_task_completed("test", 1.5)

        # Counter should be incremented
        new_value = tasks_completed.labels(queue="test")._value.get()
        assert new_value == initial + 1

    def test_record_task_completed_records_duration(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that record_task_completed records duration in histogram."""
        prometheus_metrics.record_task_completed("test", 0.5)

        # Check histogram has observations
        task_duration = prometheus_metrics.task_duration
        assert task_duration is not None
        histogram = task_duration.labels(queue="test")
        assert histogram._sum.get() >= 0.5

    def test_record_task_completed_with_different_queues(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test recording completions for different queues."""
        prometheus_metrics.record_task_completed("emails", 1.0)
        prometheus_metrics.record_task_completed("notifications", 0.5)

        tasks_completed = prometheus_metrics.tasks_completed
        assert tasks_completed is not None
        emails_count = tasks_completed.labels(queue="emails")._value.get()
        notifications_count = tasks_completed.labels(queue="notifications")._value.get()

        assert emails_count >= 1
        assert notifications_count >= 1


@pytest.mark.integration
class TestRecordTaskFailed:
    """Tests for record_task_failed method."""

    def test_record_task_failed_increments_counter(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that record_task_failed increments the failed counter."""
        tasks_failed = prometheus_metrics.tasks_failed
        assert tasks_failed is not None
        initial = tasks_failed.labels(queue="test")._value.get()

        prometheus_metrics.record_task_failed("test")

        new_value = tasks_failed.labels(queue="test")._value.get()
        assert new_value == initial + 1

    def test_record_task_failed_with_different_queues(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test recording failures for different queues."""
        prometheus_metrics.record_task_failed("emails")
        prometheus_metrics.record_task_failed("emails")
        prometheus_metrics.record_task_failed("notifications")

        tasks_failed = prometheus_metrics.tasks_failed
        assert tasks_failed is not None
        emails_count = tasks_failed.labels(queue="emails")._value.get()
        notifications_count = tasks_failed.labels(queue="notifications")._value.get()

        assert emails_count >= 2
        assert notifications_count >= 1


@pytest.mark.integration
class TestRecordTaskEnqueued:
    """Tests for record_task_enqueued method."""

    def test_record_task_enqueued_increments_counter(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that record_task_enqueued increments the enqueued counter."""
        tasks_enqueued = prometheus_metrics.tasks_enqueued
        assert tasks_enqueued is not None
        initial = tasks_enqueued.labels(queue="test")._value.get()

        prometheus_metrics.record_task_enqueued("test")

        new_value = tasks_enqueued.labels(queue="test")._value.get()
        assert new_value == initial + 1


@pytest.mark.integration
class TestUpdateFromCollector:
    """Tests for update_from_collector method."""

    def test_update_from_collector_updates_workers_active(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that update_from_collector sets workers_active gauge."""
        prometheus_metrics.update_from_collector(
            pending=10,
            running=5,
            completed=100,
            failed=3,
            active_workers=8,
            queue_depths={"emails": 20, "notifications": 15},
        )

        workers_active = prometheus_metrics.workers_active
        assert workers_active is not None
        assert workers_active._value.get() == 8

    def test_update_from_collector_updates_queue_depths(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that update_from_collector sets queue depth gauges."""
        prometheus_metrics.update_from_collector(
            pending=10,
            running=5,
            completed=100,
            failed=3,
            active_workers=8,
            queue_depths={"emails": 20, "notifications": 15},
        )

        queue_depth = prometheus_metrics.queue_depth
        assert queue_depth is not None
        emails_depth = queue_depth.labels(queue="emails")._value.get()
        notifications_depth = queue_depth.labels(queue="notifications")._value.get()

        assert emails_depth == 20
        assert notifications_depth == 15


@pytest.mark.integration
class TestGenerateLatest:
    """Tests for generate_latest method."""

    def test_generate_latest_returns_bytes(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test that generate_latest returns bytes."""
        output = prometheus_metrics.generate_latest()
        assert isinstance(output, bytes)

    def test_generate_latest_contains_namespace(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that output contains the asynctasq namespace."""
        # Record some metrics first
        prometheus_metrics.record_task_enqueued("test")

        output = prometheus_metrics.generate_latest()
        assert NAMESPACE.encode() in output

    def test_generate_latest_contains_metric_names(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that output contains expected metric names."""
        prometheus_metrics.record_task_enqueued("test")
        prometheus_metrics.record_task_completed("test", 0.5)
        prometheus_metrics.record_task_failed("test")

        output = prometheus_metrics.generate_latest()
        decoded = output.decode("utf-8")

        assert "tasks_enqueued_total" in decoded
        assert "tasks_completed_total" in decoded
        assert "tasks_failed_total" in decoded

    def test_generate_latest_prometheus_format(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test that output follows Prometheus text format."""
        prometheus_metrics.record_task_enqueued("emails")

        output = prometheus_metrics.generate_latest().decode("utf-8")

        # Prometheus format has lines like:
        # # HELP metric_name Description
        # # TYPE metric_name counter
        # metric_name{label="value"} count
        assert "# HELP" in output
        assert "# TYPE" in output


@pytest.mark.integration
class TestGlobalSingleton:
    """Tests for global singleton pattern."""

    def test_get_prometheus_metrics_returns_singleton(self) -> None:
        """Test that get_prometheus_metrics returns same instance."""
        metrics1 = get_prometheus_metrics()
        metrics2 = get_prometheus_metrics()

        assert metrics1 is metrics2

    def test_reset_prometheus_metrics_clears_singleton(self) -> None:
        """Test that reset_prometheus_metrics clears the singleton."""
        metrics1 = get_prometheus_metrics()
        reset_prometheus_metrics()
        metrics2 = get_prometheus_metrics()

        assert metrics1 is not metrics2

    def test_singleton_is_shared_across_modules(self) -> None:
        """Test that the singleton is truly global."""
        from asynctasq_monitor.services import prometheus

        metrics1 = get_prometheus_metrics()
        metrics2 = prometheus.get_prometheus_metrics()

        assert metrics1 is metrics2


@pytest.mark.integration
class TestMetricsNamespace:
    """Tests for metric namespacing."""

    def test_namespace_constant(self) -> None:
        """Test that NAMESPACE constant is correct."""
        assert NAMESPACE == "asynctasq"

    def test_metrics_use_namespace(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test that all metrics use the correct namespace."""
        prometheus_metrics.record_task_enqueued("test")

        output = prometheus_metrics.generate_latest().decode("utf-8")

        # All metrics should be prefixed with namespace
        assert "asynctasq_tasks_enqueued_total" in output


@pytest.mark.integration
class TestHistogramBuckets:
    """Tests for histogram bucket configuration."""

    def test_task_duration_has_expected_buckets(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that task_duration histogram has sensible buckets."""
        histogram = prometheus_metrics.task_duration
        assert histogram is not None

        # The buckets should be configured for task queue durations
        expected_buckets = [
            0.01,
            0.05,
            0.1,
            0.5,
            1.0,
            5.0,
            10.0,
            30.0,
            60.0,
            300.0,
            float("inf"),
        ]
        assert histogram._upper_bounds == expected_buckets

    def test_histogram_observations_in_correct_buckets(
        self, prometheus_metrics: PrometheusMetrics
    ) -> None:
        """Test that observations fall into correct buckets."""
        # Record a fast task (10ms)
        prometheus_metrics.record_task_completed("test", 0.01)

        # Record a slow task (5 seconds)
        prometheus_metrics.record_task_completed("test", 5.0)

        output = prometheus_metrics.generate_latest().decode("utf-8")
        assert "task_duration_seconds_bucket" in output


@pytest.mark.integration
class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_queue_name(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test recording metrics with empty queue name."""
        prometheus_metrics.record_task_enqueued("")
        prometheus_metrics.record_task_completed("", 0.1)
        prometheus_metrics.record_task_failed("")

        # Should not raise

    def test_special_characters_in_queue_name(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test recording metrics with special characters in queue name."""
        prometheus_metrics.record_task_enqueued("queue:emails:high-priority")
        prometheus_metrics.record_task_completed("queue:emails:high-priority", 0.1)

        # Should not raise

    def test_zero_duration(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test recording task with zero duration."""
        prometheus_metrics.record_task_completed("test", 0.0)

        # Should not raise

    def test_very_large_duration(self, prometheus_metrics: PrometheusMetrics) -> None:
        """Test recording task with very large duration."""
        prometheus_metrics.record_task_completed("test", 86400.0)  # 24 hours

        # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
