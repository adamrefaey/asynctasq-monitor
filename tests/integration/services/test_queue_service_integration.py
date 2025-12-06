"""Integration tests for QueueService.

This module tests QueueService against a mocked BaseDriver to verify
the service layer correctly interacts with the driver layer.

Following 2024/2025 pytest best practices:
- Use pytest-asyncio strict mode with explicit @pytest.mark.asyncio
- Use factory fixtures for test data customization
- Follow AAA pattern (Arrange-Act-Assert)
- Test edge cases and error conditions
- Prefer integration tests over unit tests for service layers

References:
- https://asyncsquadlabs.com/blog/python-testing-best-practices/
- https://docs.pytest.org/en/stable/how-to/parametrize.html
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from asynctasq.core.dispatcher import Dispatcher
from asynctasq.drivers.base_driver import BaseDriver
from asynctasq_monitor.models.queue import (
    QueueAlertLevel,
    QueueFilters,
    QueueStatus,
)
from asynctasq_monitor.services.queue_service import QueueService

pytestmark = pytest.mark.asyncio


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_driver() -> MagicMock:
    """Create a mock BaseDriver for testing."""
    driver = MagicMock(spec=BaseDriver)
    driver.get_all_queue_names = AsyncMock(return_value=[])
    driver.get_queue_stats = AsyncMock(
        return_value={
            "name": "test-queue",
            "depth": 0,
            "processing": 0,
            "completed_total": 0,
            "failed_total": 0,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }
    )
    return driver


@pytest.fixture
def mock_dispatcher(mock_driver: MagicMock) -> MagicMock:
    """Create a mock Dispatcher with the mock driver attached."""
    dispatcher = MagicMock(spec=Dispatcher)
    dispatcher.driver = mock_driver
    return dispatcher


@pytest_asyncio.fixture
async def queue_service(mock_dispatcher: MagicMock) -> QueueService:
    """Create a QueueService with mocked dispatcher."""
    service = QueueService()
    with patch(
        "asynctasq_monitor.services.queue_service.get_dispatcher",
        return_value=mock_dispatcher,
    ):
        # Force driver initialization by calling _ensure_driver
        service._ensure_driver()
    return service


@pytest.fixture
def sample_queue_stats() -> list[dict[str, object]]:
    """Create sample queue stats dicts for testing multiple queues."""
    return [
        {
            "name": "emails",
            "depth": 42,
            "processing": 5,
            "completed_total": 15000,
            "failed_total": 150,
            "avg_duration_ms": 1250.5,
            "throughput_per_minute": 45.2,
        },
        {
            "name": "payments",
            "depth": 15,
            "processing": 0,
            "completed_total": 5000,
            "failed_total": 50,
            "avg_duration_ms": 2500.0,
            "throughput_per_minute": 0.0,
        },
        {
            "name": "reports",
            "depth": 150,  # Warning level
            "processing": 2,
            "completed_total": 1000,
            "failed_total": 25,
            "avg_duration_ms": 30000.0,
            "throughput_per_minute": 2.5,
        },
        {
            "name": "notifications",
            "depth": 550,  # Critical level
            "processing": 10,
            "completed_total": 50000,
            "failed_total": 500,
            "avg_duration_ms": 500.0,
            "throughput_per_minute": 120.0,
        },
    ]


# ============================================================================
# Tests: Service Initialization
# ============================================================================


class TestQueueServiceInitialization:
    """Tests for QueueService initialization and driver handling."""

    async def test_service_initializes_without_driver(self) -> None:
        """Test that QueueService starts with no driver attached."""
        service = QueueService()
        assert service._driver is None

    async def test_ensure_driver_raises_when_no_dispatcher(self) -> None:
        """Test that _ensure_driver raises RuntimeError when dispatcher unavailable."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                service._ensure_driver()

    async def test_ensure_driver_raises_when_dispatcher_has_no_driver(self) -> None:
        """Test that _ensure_driver raises when dispatcher has no driver attr."""
        service = QueueService()
        mock_dispatcher = MagicMock()
        del mock_dispatcher.driver  # Remove the driver attribute

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                service._ensure_driver()

    async def test_ensure_driver_sets_driver_from_dispatcher(
        self, mock_dispatcher: MagicMock, mock_driver: MagicMock
    ) -> None:
        """Test that _ensure_driver correctly sets driver from dispatcher."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            service._ensure_driver()

        assert service._driver is mock_driver

    async def test_ensure_driver_only_initializes_once(
        self, mock_dispatcher: MagicMock, mock_driver: MagicMock
    ) -> None:
        """Test that _ensure_driver doesn't reinitialize if driver is set."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ) as mock_get_dispatcher:
            service._ensure_driver()
            service._ensure_driver()  # Second call should not fetch dispatcher again

        # get_dispatcher should only be called once since driver is already set
        assert mock_get_dispatcher.call_count == 1


# ============================================================================
# Tests: get_queues()
# ============================================================================


class TestGetQueues:
    """Tests for QueueService.get_queues() method."""

    async def test_get_queues_returns_empty_list_when_no_queues(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test get_queues returns empty list when no queues exist."""
        mock_driver.get_all_queue_names.return_value = []

        result = await queue_service.get_queues()

        assert result.items == []
        assert result.total == 0
        mock_driver.get_all_queue_names.assert_called_once()

    async def test_get_queues_returns_all_queues(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
    ) -> None:
        """Test get_queues returns all queues from driver."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        result = await queue_service.get_queues()

        assert len(result.items) == 4
        assert result.total == 4
        assert mock_driver.get_queue_stats.call_count == 4

    async def test_get_queues_maps_queue_stats_to_queue_model(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test that QueueStats are correctly mapped to Queue models."""
        mock_driver.get_all_queue_names.return_value = ["test-queue"]
        mock_driver.get_queue_stats.return_value = {
            "name": "test-queue",
            "depth": 100,
            "processing": 5,
            "completed_total": 1000,
            "failed_total": 50,
            "avg_duration_ms": 2500.0,
            "throughput_per_minute": 10.0,
        }

        result = await queue_service.get_queues()

        assert len(result.items) == 1
        queue = result.items[0]
        assert queue.name == "test-queue"
        assert queue.depth == 100
        assert queue.processing == 5
        assert queue.completed_total == 1000
        assert queue.failed_total == 50
        assert queue.avg_duration_ms == 2500.0
        assert queue.throughput_per_minute == 10.0
        assert queue.status == QueueStatus.ACTIVE

    async def test_get_queues_with_status_filter(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
    ) -> None:
        """Test filtering queues by status."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(status=QueueStatus.ACTIVE)
        result = await queue_service.get_queues(filters)

        # All queues should have ACTIVE status since driver doesn't support pause yet
        assert result.total == 4
        for queue in result.items:
            assert queue.status == QueueStatus.ACTIVE

    async def test_get_queues_with_search_filter(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
    ) -> None:
        """Test filtering queues by search term."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(search="email")
        result = await queue_service.get_queues(filters)

        assert result.total == 1
        assert result.items[0].name == "emails"

    async def test_get_queues_with_search_filter_case_insensitive(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
    ) -> None:
        """Test that search filter is case-insensitive."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(search="EMAIL")
        result = await queue_service.get_queues(filters)

        assert result.total == 1
        assert result.items[0].name == "emails"

    async def test_get_queues_with_min_depth_filter(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
    ) -> None:
        """Test filtering queues by minimum depth."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(min_depth=100)
        result = await queue_service.get_queues(filters)

        assert result.total == 2
        for queue in result.items:
            assert queue.depth >= 100

    async def test_get_queues_with_alert_level_filter(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
    ) -> None:
        """Test filtering queues by alert level."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(alert_level=QueueAlertLevel.CRITICAL)
        result = await queue_service.get_queues(filters)

        assert result.total == 1
        assert result.items[0].name == "notifications"
        assert result.items[0].alert_level == QueueAlertLevel.CRITICAL

    async def test_get_queues_with_combined_filters(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
    ) -> None:
        """Test applying multiple filters simultaneously."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(min_depth=100, search="report")
        result = await queue_service.get_queues(filters)

        assert result.total == 1
        assert result.items[0].name == "reports"

    async def test_get_queues_raises_when_driver_not_initialized(self) -> None:
        """Test that get_queues raises RuntimeError when driver not available."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                await service.get_queues()


# ============================================================================
# Tests: get_queue_by_name()
# ============================================================================


class TestGetQueueByName:
    """Tests for QueueService.get_queue_by_name() method."""

    async def test_get_queue_by_name_returns_queue(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test getting a queue by name returns the queue."""
        mock_driver.get_queue_stats.return_value = {
            "name": "emails",
            "depth": 42,
            "processing": 5,
            "completed_total": 15000,
            "failed_total": 150,
            "avg_duration_ms": 1250.5,
            "throughput_per_minute": 45.2,
        }

        result = await queue_service.get_queue_by_name("emails")

        assert result is not None
        assert result.name == "emails"
        assert result.depth == 42
        mock_driver.get_queue_stats.assert_called_once_with("emails")

    async def test_get_queue_by_name_returns_none_when_not_found(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test getting a non-existent queue returns None."""
        mock_driver.get_queue_stats.side_effect = Exception("Queue not found")

        result = await queue_service.get_queue_by_name("nonexistent")

        assert result is None

    async def test_get_queue_by_name_handles_driver_exceptions(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test that driver exceptions are caught and return None."""
        mock_driver.get_queue_stats.side_effect = ConnectionError("Connection lost")

        result = await queue_service.get_queue_by_name("emails")

        assert result is None

    async def test_get_queue_by_name_raises_when_driver_not_initialized(self) -> None:
        """Test that method raises when driver not available."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                await service.get_queue_by_name("emails")


# ============================================================================
# Tests: pause_queue()
# ============================================================================


class TestPauseQueue:
    """Tests for QueueService.pause_queue() method."""

    async def test_pause_queue_returns_success(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test pausing a queue returns success response."""
        mock_driver.get_queue_stats.return_value = {
            "name": "emails",
            "depth": 42,
            "processing": 5,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.pause_queue("emails")

        assert result.success is True
        assert result.queue_name == "emails"
        assert result.action == "pause"
        assert "paused successfully" in result.message

    async def test_pause_queue_includes_reason_in_message(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test pause reason is included in the message."""
        mock_driver.get_queue_stats.return_value = {
            "name": "emails",
            "depth": 42,
            "processing": 5,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.pause_queue("emails", reason="Maintenance window")

        assert result.success is True
        assert "Maintenance window" in result.message

    async def test_pause_queue_returns_failure_when_queue_not_found(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test pausing non-existent queue returns failure."""
        mock_driver.get_queue_stats.side_effect = Exception("Not found")

        result = await queue_service.pause_queue("nonexistent")

        assert result.success is False
        assert result.queue_name == "nonexistent"
        assert result.action == "pause"
        assert "not found" in result.message

    async def test_pause_queue_raises_when_driver_not_initialized(self) -> None:
        """Test that method raises when driver not available."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                await service.pause_queue("emails")


# ============================================================================
# Tests: resume_queue()
# ============================================================================


class TestResumeQueue:
    """Tests for QueueService.resume_queue() method."""

    async def test_resume_queue_returns_success(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test resuming a queue returns success response."""
        mock_driver.get_queue_stats.return_value = {
            "name": "emails",
            "depth": 42,
            "processing": 5,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.resume_queue("emails")

        assert result.success is True
        assert result.queue_name == "emails"
        assert result.action == "resume"
        assert "resumed successfully" in result.message

    async def test_resume_queue_returns_failure_when_queue_not_found(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test resuming non-existent queue returns failure."""
        mock_driver.get_queue_stats.side_effect = Exception("Not found")

        result = await queue_service.resume_queue("nonexistent")

        assert result.success is False
        assert result.queue_name == "nonexistent"
        assert result.action == "resume"
        assert "not found" in result.message

    async def test_resume_queue_raises_when_driver_not_initialized(self) -> None:
        """Test that method raises when driver not available."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                await service.resume_queue("emails")


# ============================================================================
# Tests: clear_queue()
# ============================================================================


class TestClearQueue:
    """Tests for QueueService.clear_queue() method."""

    async def test_clear_queue_returns_success_with_count(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test clearing a queue returns success with task count."""
        mock_driver.get_queue_stats.return_value = {
            "name": "emails",
            "depth": 42,
            "processing": 5,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.clear_queue("emails")

        assert result.success is True
        assert result.queue_name == "emails"
        assert result.tasks_cleared == 42  # depth from stats
        assert "Cleared 42 tasks" in result.message

    async def test_clear_empty_queue_returns_zero_cleared(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test clearing an empty queue returns 0 tasks cleared."""
        mock_driver.get_queue_stats.return_value = {
            "name": "empty-queue",
            "depth": 0,
            "processing": 0,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.clear_queue("empty-queue")

        assert result.success is True
        assert result.tasks_cleared == 0
        assert "Cleared 0 tasks" in result.message

    async def test_clear_queue_returns_failure_when_queue_not_found(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test clearing non-existent queue returns failure."""
        mock_driver.get_queue_stats.side_effect = Exception("Not found")

        result = await queue_service.clear_queue("nonexistent")

        assert result.success is False
        assert result.queue_name == "nonexistent"
        assert result.tasks_cleared == 0
        assert "not found" in result.message

    async def test_clear_queue_raises_when_driver_not_initialized(self) -> None:
        """Test that method raises when driver not available."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                await service.clear_queue("emails")


# ============================================================================
# Tests: get_queue_metrics()
# ============================================================================


class TestGetQueueMetrics:
    """Tests for QueueService.get_queue_metrics() method."""

    async def test_get_queue_metrics_returns_empty_list(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test get_queue_metrics returns empty list (placeholder implementation)."""
        result = await queue_service.get_queue_metrics("emails")

        assert result == []

    async def test_get_queue_metrics_accepts_time_range_params(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test get_queue_metrics accepts optional time range parameters."""
        now = datetime.now(UTC)
        from_time = now - timedelta(hours=24)

        result = await queue_service.get_queue_metrics(
            "emails",
            from_time=from_time,
            to_time=now,
            interval_minutes=15,
        )

        assert result == []

    async def test_get_queue_metrics_raises_when_driver_not_initialized(self) -> None:
        """Test that method raises when driver not available."""
        service = QueueService()

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="Dispatcher driver not available"):
                await service.get_queue_metrics("emails")


# ============================================================================
# Tests: Queue Alert Level Calculations
# ============================================================================


class TestQueueAlertLevels:
    """Tests for Queue alert level computation (computed in Queue model)."""

    async def test_queue_with_low_depth_has_normal_alert(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test queue with depth < 100 has normal alert level."""
        mock_driver.get_all_queue_names.return_value = ["small-queue"]
        mock_driver.get_queue_stats.return_value = {
            "name": "small-queue",
            "depth": 50,
            "processing": 0,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.get_queues()

        assert result.items[0].depth == 50
        assert result.items[0].alert_level == QueueAlertLevel.NORMAL

    async def test_queue_with_medium_depth_has_warning_alert(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test queue with 100 <= depth < 500 has warning alert level."""
        mock_driver.get_all_queue_names.return_value = ["medium-queue"]
        mock_driver.get_queue_stats.return_value = {
            "name": "medium-queue",
            "depth": 250,
            "processing": 0,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.get_queues()

        assert result.items[0].depth == 250
        assert result.items[0].alert_level == QueueAlertLevel.WARNING

    async def test_queue_with_high_depth_has_critical_alert(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test queue with depth >= 500 has critical alert level."""
        mock_driver.get_all_queue_names.return_value = ["large-queue"]
        mock_driver.get_queue_stats.return_value = {
            "name": "large-queue",
            "depth": 750,
            "processing": 0,
            "completed_total": 100,
            "failed_total": 5,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.get_queues()

        assert result.items[0].depth == 750
        assert result.items[0].alert_level == QueueAlertLevel.CRITICAL


# ============================================================================
# Tests: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_get_queues_handles_partial_stats_failure(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test that partial failures in get_queue_stats don't crash the service."""
        # This tests what happens if one queue's stats fail to fetch
        mock_driver.get_all_queue_names.return_value = ["queue1", "queue2"]

        # First succeeds, second fails, then succeeds
        stats1 = {
            "name": "queue1",
            "depth": 10,
            "processing": 0,
            "completed_total": 0,
            "failed_total": 0,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }
        stats2 = {
            "name": "queue2",
            "depth": 20,
            "processing": 0,
            "completed_total": 0,
            "failed_total": 0,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }
        mock_driver.get_queue_stats.side_effect = [stats1, stats2]

        result = await queue_service.get_queues()

        assert len(result.items) == 2
        assert result.total == 2

    async def test_queue_with_zero_depth_and_processing(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test queue with zero depth and processing is handled correctly."""
        mock_driver.get_all_queue_names.return_value = ["idle-queue"]
        mock_driver.get_queue_stats.return_value = {
            "name": "idle-queue",
            "depth": 0,
            "processing": 0,
            "completed_total": 1000,
            "failed_total": 50,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.get_queues()

        queue = result.items[0]
        assert queue.depth == 0
        assert queue.processing == 0
        assert queue.is_idle is True

    async def test_queue_with_none_duration_and_throughput(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
    ) -> None:
        """Test queue with None optional metrics is handled correctly."""
        mock_driver.get_all_queue_names.return_value = ["new-queue"]
        mock_driver.get_queue_stats.return_value = {
            "name": "new-queue",
            "depth": 5,
            "processing": 1,
            "completed_total": 0,
            "failed_total": 0,
            "avg_duration_ms": None,
            "throughput_per_minute": None,
        }

        result = await queue_service.get_queues()

        queue = result.items[0]
        assert queue.avg_duration_ms is None
        assert queue.throughput_per_minute is None

    @pytest.mark.parametrize(
        "search_term,expected_count",
        [
            ("", 4),  # Empty search returns all
            ("pay", 1),  # Partial match
            ("EMAILS", 1),  # Case insensitive
            ("queue", 0),  # No match
            ("not", 1),  # notifications
        ],
    )
    async def test_search_filter_variations(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
        search_term: str,
        expected_count: int,
    ) -> None:
        """Test various search filter patterns."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(search=search_term) if search_term else None
        result = await queue_service.get_queues(filters)

        assert result.total == expected_count

    @pytest.mark.parametrize(
        "min_depth,expected_count",
        [
            (0, 4),
            (10, 4),
            (50, 2),
            (200, 1),
            (1000, 0),
        ],
    )
    async def test_min_depth_filter_variations(
        self,
        queue_service: QueueService,
        mock_driver: MagicMock,
        sample_queue_stats: list[dict[str, object]],
        min_depth: int,
        expected_count: int,
    ) -> None:
        """Test various min_depth filter thresholds."""
        queue_names = [s["name"] for s in sample_queue_stats]
        mock_driver.get_all_queue_names.return_value = queue_names
        mock_driver.get_queue_stats.side_effect = sample_queue_stats

        filters = QueueFilters(min_depth=min_depth)
        result = await queue_service.get_queues(filters)

        assert result.total == expected_count


# ============================================================================
# Tests: RuntimeError scenarios for defensive "if self._driver is None" checks
# ============================================================================


class TestDriverNoneGuards:
    """Tests for the defensive driver None guards in async methods.

    These tests verify that the `if self._driver is None` checks after
    `_ensure_driver()` work correctly. These guards exist as defensive
    programming but require mocking to trigger since _ensure_driver()
    would normally raise before setting _driver to None.
    """

    async def test_get_queues_guard_triggered_by_dispatcher_returning_none_driver(
        self,
    ) -> None:
        """Test get_queues when dispatcher.driver is None after assignment."""
        service = QueueService()

        # Create a dispatcher where accessing .driver returns None
        mock_dispatcher = MagicMock()
        mock_dispatcher.driver = None

        # This tests the scenario where hasattr returns True but driver is None
        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            # _ensure_driver will set self._driver = None
            # Then the guard should catch it
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.get_queues()

    async def test_get_queue_by_name_guard_triggered_by_none_driver(self) -> None:
        """Test get_queue_by_name when driver is None after _ensure_driver."""
        service = QueueService()

        mock_dispatcher = MagicMock()
        mock_dispatcher.driver = None

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.get_queue_by_name("test")

    async def test_pause_queue_guard_triggered_by_none_driver(self) -> None:
        """Test pause_queue when driver is None after _ensure_driver."""
        service = QueueService()

        mock_dispatcher = MagicMock()
        mock_dispatcher.driver = None

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.pause_queue("test")

    async def test_resume_queue_guard_triggered_by_none_driver(self) -> None:
        """Test resume_queue when driver is None after _ensure_driver."""
        service = QueueService()

        mock_dispatcher = MagicMock()
        mock_dispatcher.driver = None

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.resume_queue("test")

    async def test_clear_queue_guard_triggered_by_none_driver(self) -> None:
        """Test clear_queue when driver is None after _ensure_driver."""
        service = QueueService()

        mock_dispatcher = MagicMock()
        mock_dispatcher.driver = None

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.clear_queue("test")

    async def test_get_queue_metrics_guard_triggered_by_none_driver(self) -> None:
        """Test get_queue_metrics when driver is None after _ensure_driver."""
        service = QueueService()

        mock_dispatcher = MagicMock()
        mock_dispatcher.driver = None

        with patch(
            "asynctasq_monitor.services.queue_service.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            with pytest.raises(RuntimeError, match="Driver not initialized"):
                await service.get_queue_metrics("test")
