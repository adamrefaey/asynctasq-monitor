"""Tests for MetricsCollector service.

Following pytest best practices:
- Use explicit @pytest.mark.asyncio decorators (strict mode)
- Use pytest.mark.unit for categorization
- Test lifecycle (start/stop)
- Mock external dependencies
"""

import asyncio
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from async_task_q_monitor.services.metrics_collector import MetricsCollector

if TYPE_CHECKING:
    from async_task_q_monitor.websocket.manager import ConnectionManager


class MockConnectionManager:
    """Mock ConnectionManager for testing."""

    def __init__(self) -> None:
        """Initialize mock manager."""
        self.broadcast_to_room = AsyncMock(return_value=1)
        self.broadcast_to_rooms = AsyncMock(return_value=1)


@pytest.fixture
def mock_manager() -> MockConnectionManager:
    """Create a mock connection manager."""
    return MockConnectionManager()


@pytest.fixture
def collector(mock_manager: MockConnectionManager) -> MetricsCollector:
    """Create a MetricsCollector with mock manager and short interval."""
    return MetricsCollector(
        poll_interval=0.1,  # Short interval for tests
        connection_manager=cast("ConnectionManager", mock_manager),
    )


@pytest.mark.unit
class TestMetricsCollectorLifecycle:
    """Tests for MetricsCollector start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_task(self, collector: MetricsCollector) -> None:
        """Test that start() creates background task."""
        assert not collector.is_running

        await collector.start()

        try:
            assert collector.is_running
        finally:
            await collector.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, collector: MetricsCollector) -> None:
        """Test that stop() cancels background task."""
        await collector.start()
        assert collector.is_running

        await collector.stop()

        assert not collector.is_running

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, collector: MetricsCollector) -> None:
        """Test that calling start() twice is safe."""
        await collector.start()
        await collector.start()  # Should not raise

        try:
            assert collector.is_running
        finally:
            await collector.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, collector: MetricsCollector) -> None:
        """Test that stop() when not running is safe."""
        assert not collector.is_running

        await collector.stop()  # Should not raise

        assert not collector.is_running


@pytest.mark.unit
class TestMetricsCollectorCollection:
    """Tests for metrics collection functionality."""

    @pytest.mark.asyncio
    async def test_get_stub_metrics(self, collector: MetricsCollector) -> None:
        """Test stub metrics when driver not available."""
        metrics = collector._get_stub_metrics()

        assert metrics["pending"] == 0
        assert metrics["running"] == 0
        assert metrics["completed"] == 0
        assert metrics["failed"] == 0
        assert metrics["success_rate"] == 100.0
        assert metrics["active_workers"] == 0
        assert metrics["queue_depths"] == {}
        assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_get_last_metrics_initially_empty(self, collector: MetricsCollector) -> None:
        """Test get_last_metrics returns empty dict initially."""
        metrics = collector.get_last_metrics()
        assert metrics == {}

    @pytest.mark.asyncio
    async def test_collect_metrics_without_driver(self, collector: MetricsCollector) -> None:
        """Test _collect_metrics returns None when dispatcher returns None."""
        # Mock the entire import chain to simulate no dispatcher available
        mock_dispatcher_module = MagicMock()
        mock_dispatcher_module.get_dispatcher.return_value = None

        with patch.dict("sys.modules", {"async_task_q.core.dispatcher": mock_dispatcher_module}):
            metrics = await collector._collect_metrics()

            # Should return None when dispatcher is None
            assert metrics is None


@pytest.mark.unit
class TestMetricsCollectorBroadcasting:
    """Tests for metrics broadcasting functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_metrics_to_global_room(
        self,
        collector: MetricsCollector,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test that metrics are broadcast to global room."""
        metrics = {
            "pending": 10,
            "running": 2,
            "completed": 100,
            "failed": 5,
            "success_rate": 95.24,
            "active_workers": 3,
            "queue_depths": {},
            "timestamp": "2025-12-02T10:00:00Z",
        }

        await collector._broadcast_metrics(metrics)

        # Should broadcast global metrics
        mock_manager.broadcast_to_room.assert_called_once()
        call_args = mock_manager.broadcast_to_room.call_args
        assert call_args[0][0] == "global"

    @pytest.mark.asyncio
    async def test_broadcast_queue_depths_to_queue_rooms(
        self,
        collector: MetricsCollector,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test that queue depths are broadcast to queue rooms."""
        metrics = {
            "pending": 10,
            "running": 2,
            "completed": 100,
            "failed": 5,
            "success_rate": 95.24,
            "active_workers": 3,
            "queue_depths": {"emails": 50, "orders": 100},
            "timestamp": "2025-12-02T10:00:00Z",
        }

        await collector._broadcast_metrics(metrics)

        # Should broadcast to each queue room
        # 1 call for global + 2 calls for queue rooms
        assert mock_manager.broadcast_to_room.call_count == 1  # global
        assert mock_manager.broadcast_to_rooms.call_count == 2  # queue rooms


@pytest.mark.unit
class TestMetricsCollectorPolling:
    """Tests for metrics polling loop."""

    @pytest.mark.asyncio
    async def test_collector_polls_at_interval(
        self,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test that collector polls at configured interval."""
        collector = MetricsCollector(
            poll_interval=0.05,  # 50ms for fast test
            connection_manager=cast("ConnectionManager", mock_manager),
        )

        # Mock _collect_and_broadcast to count calls
        call_count = 0

        async def mock_collect() -> None:
            nonlocal call_count
            call_count += 1

        collector._collect_and_broadcast = mock_collect  # type: ignore

        await collector.start()

        # Wait for a few poll cycles
        await asyncio.sleep(0.2)

        await collector.stop()

        # Should have polled multiple times
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_collector_handles_collection_errors(
        self,
        mock_manager: MockConnectionManager,
    ) -> None:
        """Test that collector continues after collection errors."""
        collector = MetricsCollector(
            poll_interval=0.05,
            connection_manager=cast("ConnectionManager", mock_manager),
        )

        call_count = 0

        async def mock_collect_with_error() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Test error")

        collector._collect_and_broadcast = mock_collect_with_error  # type: ignore

        await collector.start()

        # Wait for a few poll cycles
        await asyncio.sleep(0.2)

        await collector.stop()

        # Should continue polling despite error
        assert call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "unit"])
