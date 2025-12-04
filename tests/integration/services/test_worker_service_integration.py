"""Integration tests for WorkerService.

This module tests WorkerService with comprehensive coverage of all
functionality following 2024/2025 pytest best practices:

- Use pytest-asyncio strict mode with explicit @pytest.mark.asyncio
- Use factory fixtures for test data customization
- Follow AAA pattern (Arrange-Act-Assert)
- Test edge cases and error conditions
- Prefer integration tests over unit tests for service layers
- Use parametrize for testing multiple scenarios

References:
- https://fastapi.tiangolo.com/advanced/async-tests/
- https://docs.pytest.org/en/stable/how-to/parametrize.html
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from asynctasq_monitor.models.worker import (
    HeartbeatRequest,
    WorkerAction,
    WorkerFilters,
    WorkerStatus,
)
from asynctasq_monitor.services.worker_service import WorkerService

pytestmark = pytest.mark.asyncio


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def worker_service() -> WorkerService:
    """Create a fresh WorkerService with mock data for each test."""
    return WorkerService()


@pytest.fixture
def now() -> datetime:
    """Get current UTC datetime for consistent test timestamps."""
    return datetime.now(UTC)


# ============================================================================
# Tests: Service Initialization
# ============================================================================


class TestWorkerServiceInitialization:
    """Tests for WorkerService initialization and mock data setup."""

    async def test_service_initializes_with_mock_workers(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that WorkerService initializes with mock workers."""
        assert len(worker_service._workers) > 0

    async def test_service_initializes_worker_logs_storage(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that worker logs storage is initialized for each worker."""
        for worker_id in worker_service._workers:
            assert worker_id in worker_service._worker_logs

    async def test_service_initializes_pending_actions_storage(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that pending actions storage is initialized for each worker."""
        for worker_id in worker_service._workers:
            assert worker_id in worker_service._pending_actions
            assert "pause" in worker_service._pending_actions[worker_id]
            assert "shutdown" in worker_service._pending_actions[worker_id]

    async def test_mock_workers_have_diverse_statuses(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that mock data includes workers with different statuses."""
        statuses = {w.status for w in worker_service._workers.values()}
        assert WorkerStatus.ACTIVE in statuses
        assert WorkerStatus.IDLE in statuses
        assert WorkerStatus.OFFLINE in statuses


# ============================================================================
# Tests: get_workers()
# ============================================================================


class TestGetWorkers:
    """Tests for WorkerService.get_workers() method."""

    async def test_get_workers_returns_all_workers(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test get_workers returns all workers when no filters applied."""
        result = await worker_service.get_workers()

        assert result.total == len(worker_service._workers)
        assert len(result.items) == result.total

    async def test_get_workers_returns_workers_sorted_by_status_then_name(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that workers are sorted by status priority then name."""
        result = await worker_service.get_workers()

        # Active workers should come first
        active_idx = next(
            (i for i, w in enumerate(result.items) if w.status == WorkerStatus.ACTIVE),
            None,
        )
        offline_idx = next(
            (i for i, w in enumerate(result.items) if w.status == WorkerStatus.OFFLINE),
            None,
        )

        if active_idx is not None and offline_idx is not None:
            assert active_idx < offline_idx

    async def test_get_workers_with_status_filter_active(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers by ACTIVE status."""
        filters = WorkerFilters(status=WorkerStatus.ACTIVE)
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.status == WorkerStatus.ACTIVE

    async def test_get_workers_with_status_filter_idle(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers by IDLE status."""
        filters = WorkerFilters(status=WorkerStatus.IDLE)
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.status == WorkerStatus.IDLE

    async def test_get_workers_with_status_filter_offline(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers by OFFLINE status."""
        filters = WorkerFilters(status=WorkerStatus.OFFLINE)
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.status == WorkerStatus.OFFLINE

    async def test_get_workers_with_queue_filter(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers by queue name."""
        filters = WorkerFilters(queue="emails")
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert "emails" in worker.queues

    async def test_get_workers_with_queue_filter_no_matches(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering by non-existent queue returns empty list."""
        filters = WorkerFilters(queue="nonexistent-queue")
        result = await worker_service.get_workers(filters)

        assert result.total == 0
        assert result.items == []

    async def test_get_workers_with_search_filter_by_name(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test searching workers by name."""
        filters = WorkerFilters(search="prod-01")
        result = await worker_service.get_workers(filters)

        assert result.total > 0
        for worker in result.items:
            assert "prod-01" in worker.name.lower()

    async def test_get_workers_with_search_filter_by_id(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test searching workers by ID."""
        filters = WorkerFilters(search="worker-001")
        result = await worker_service.get_workers(filters)

        assert result.total == 1
        assert result.items[0].id == "worker-001"

    async def test_get_workers_with_search_filter_by_hostname(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test searching workers by hostname."""
        filters = WorkerFilters(search="server-01")
        result = await worker_service.get_workers(filters)

        assert result.total > 0
        for worker in result.items:
            assert worker.hostname is not None
            assert "server-01" in worker.hostname.lower()

    async def test_get_workers_search_is_case_insensitive(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that search filter is case insensitive."""
        filters_lower = WorkerFilters(search="prod")
        filters_upper = WorkerFilters(search="PROD")

        result_lower = await worker_service.get_workers(filters_lower)
        result_upper = await worker_service.get_workers(filters_upper)

        assert result_lower.total == result_upper.total
        assert [w.id for w in result_lower.items] == [w.id for w in result_upper.items]

    async def test_get_workers_with_is_paused_filter_true(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers that are paused."""
        # First, pause a worker
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)

        filters = WorkerFilters(is_paused=True)
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.is_paused is True

    async def test_get_workers_with_is_paused_filter_false(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers that are not paused."""
        filters = WorkerFilters(is_paused=False)
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.is_paused is False

    async def test_get_workers_with_has_current_task_filter_true(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers with current task."""
        filters = WorkerFilters(has_current_task=True)
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.current_task_id is not None

    async def test_get_workers_with_has_current_task_filter_false(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering workers without current task."""
        filters = WorkerFilters(has_current_task=False)
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.current_task_id is None

    async def test_get_workers_with_combined_filters(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test applying multiple filters simultaneously."""
        filters = WorkerFilters(
            status=WorkerStatus.ACTIVE,
            has_current_task=True,
        )
        result = await worker_service.get_workers(filters)

        for worker in result.items:
            assert worker.status == WorkerStatus.ACTIVE
            assert worker.current_task_id is not None

    async def test_get_workers_with_none_filters(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test get_workers with None filters returns all workers."""
        result = await worker_service.get_workers(None)
        assert result.total == len(worker_service._workers)


# ============================================================================
# Tests: get_worker_by_id()
# ============================================================================


class TestGetWorkerById:
    """Tests for WorkerService.get_worker_by_id() method."""

    async def test_get_worker_by_id_returns_worker(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test getting an existing worker by ID."""
        result = await worker_service.get_worker_by_id("worker-001")

        assert result is not None
        assert result.id == "worker-001"
        assert result.name == "worker-prod-01"

    async def test_get_worker_by_id_returns_none_for_nonexistent(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test getting a non-existent worker returns None."""
        result = await worker_service.get_worker_by_id("nonexistent-worker")
        assert result is None

    async def test_get_worker_by_id_returns_complete_worker_data(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that returned worker has all expected fields."""
        result = await worker_service.get_worker_by_id("worker-001")

        assert result is not None
        assert result.id is not None
        assert result.name is not None
        assert result.status is not None
        assert result.last_heartbeat is not None


# ============================================================================
# Tests: get_worker_detail()
# ============================================================================


class TestGetWorkerDetail:
    """Tests for WorkerService.get_worker_detail() method."""

    async def test_get_worker_detail_returns_detail_for_existing_worker(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test getting detailed info for existing worker."""
        result = await worker_service.get_worker_detail("worker-001")

        assert result is not None
        assert result.id == "worker-001"

    async def test_get_worker_detail_returns_none_for_nonexistent(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test getting detail for non-existent worker returns None."""
        result = await worker_service.get_worker_detail("nonexistent-worker")
        assert result is None

    async def test_get_worker_detail_includes_recent_tasks(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that detail includes recent task history."""
        result = await worker_service.get_worker_detail("worker-001")

        assert result is not None
        assert hasattr(result, "recent_tasks")
        assert isinstance(result.recent_tasks, list)
        assert len(result.recent_tasks) > 0

    async def test_get_worker_detail_includes_hourly_throughput(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that detail includes hourly throughput data."""
        result = await worker_service.get_worker_detail("worker-001")

        assert result is not None
        assert hasattr(result, "hourly_throughput")
        assert isinstance(result.hourly_throughput, list)
        assert len(result.hourly_throughput) == 24  # 24 hours of data

    async def test_get_worker_detail_recent_tasks_have_required_fields(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that recent tasks have all required fields."""
        result = await worker_service.get_worker_detail("worker-001")

        assert result is not None
        for task in result.recent_tasks:
            assert task.id is not None
            assert task.name is not None
            assert task.queue is not None
            assert task.status is not None
            assert task.started_at is not None

    async def test_get_worker_detail_hourly_throughput_format(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that hourly throughput data has correct format."""
        result = await worker_service.get_worker_detail("worker-001")

        assert result is not None
        for entry in result.hourly_throughput:
            assert "hour" in entry
            assert "count" in entry


# ============================================================================
# Tests: perform_action() - PAUSE
# ============================================================================


class TestPerformActionPause:
    """Tests for WorkerService.perform_action() with PAUSE action."""

    async def test_pause_active_worker_succeeds(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test pausing an active worker succeeds."""
        result = await worker_service.perform_action("worker-001", WorkerAction.PAUSE)

        assert result.success is True
        assert result.worker_id == "worker-001"
        assert result.action == WorkerAction.PAUSE
        assert "paused" in result.message.lower()

    async def test_pause_sets_is_paused_flag(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that pause action sets is_paused flag on worker."""
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.is_paused is True

    async def test_pause_sets_pending_action(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that pause action sets pending action flag."""
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)

        assert worker_service._pending_actions["worker-001"]["pause"] is True

    async def test_pause_offline_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test pausing an offline worker fails."""
        result = await worker_service.perform_action("worker-005", WorkerAction.PAUSE)

        assert result.success is False
        assert "Cannot pause offline worker" in result.message

    async def test_pause_already_paused_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test pausing an already paused worker fails."""
        # First pause
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)
        # Try to pause again
        result = await worker_service.perform_action("worker-001", WorkerAction.PAUSE)

        assert result.success is False
        assert "already paused" in result.message.lower()

    async def test_pause_nonexistent_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test pausing a non-existent worker fails."""
        result = await worker_service.perform_action("nonexistent", WorkerAction.PAUSE)

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_pause_idle_worker_succeeds(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test pausing an idle worker succeeds."""
        result = await worker_service.perform_action("worker-003", WorkerAction.PAUSE)

        assert result.success is True
        assert result.action == WorkerAction.PAUSE


# ============================================================================
# Tests: perform_action() - RESUME
# ============================================================================


class TestPerformActionResume:
    """Tests for WorkerService.perform_action() with RESUME action."""

    async def test_resume_paused_worker_succeeds(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test resuming a paused worker succeeds."""
        # First pause
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)
        # Then resume
        result = await worker_service.perform_action("worker-001", WorkerAction.RESUME)

        assert result.success is True
        assert result.worker_id == "worker-001"
        assert result.action == WorkerAction.RESUME
        assert "resumed" in result.message.lower()

    async def test_resume_clears_is_paused_flag(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that resume action clears is_paused flag."""
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)
        await worker_service.perform_action("worker-001", WorkerAction.RESUME)

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.is_paused is False

    async def test_resume_clears_pending_action(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that resume action clears pending pause flag."""
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)
        await worker_service.perform_action("worker-001", WorkerAction.RESUME)

        assert worker_service._pending_actions["worker-001"]["pause"] is False

    async def test_resume_not_paused_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test resuming a worker that is not paused fails."""
        result = await worker_service.perform_action("worker-001", WorkerAction.RESUME)

        assert result.success is False
        assert "not paused" in result.message.lower()

    async def test_resume_nonexistent_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test resuming a non-existent worker fails."""
        result = await worker_service.perform_action("nonexistent", WorkerAction.RESUME)

        assert result.success is False
        assert "not found" in result.message.lower()


# ============================================================================
# Tests: perform_action() - SHUTDOWN
# ============================================================================


class TestPerformActionShutdown:
    """Tests for WorkerService.perform_action() with SHUTDOWN action."""

    async def test_shutdown_active_worker_succeeds(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test graceful shutdown of active worker succeeds."""
        result = await worker_service.perform_action("worker-001", WorkerAction.SHUTDOWN)

        assert result.success is True
        assert result.worker_id == "worker-001"
        assert result.action == WorkerAction.SHUTDOWN
        assert "shutdown" in result.message.lower()
        assert "after current task" in result.message.lower()

    async def test_shutdown_sets_pending_action(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that shutdown sets pending shutdown flag."""
        await worker_service.perform_action("worker-001", WorkerAction.SHUTDOWN)

        assert worker_service._pending_actions["worker-001"]["shutdown"] is True

    async def test_shutdown_offline_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test shutdown of offline worker fails."""
        result = await worker_service.perform_action("worker-005", WorkerAction.SHUTDOWN)

        assert result.success is False
        assert "already offline" in result.message.lower()

    async def test_shutdown_nonexistent_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test shutdown of non-existent worker fails."""
        result = await worker_service.perform_action("nonexistent", WorkerAction.SHUTDOWN)

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_shutdown_idle_worker_succeeds(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test shutdown of idle worker succeeds."""
        result = await worker_service.perform_action("worker-003", WorkerAction.SHUTDOWN)

        assert result.success is True
        assert result.action == WorkerAction.SHUTDOWN


# ============================================================================
# Tests: perform_action() - KILL
# ============================================================================


class TestPerformActionKill:
    """Tests for WorkerService.perform_action() with KILL action."""

    async def test_kill_active_worker_succeeds(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test immediate kill of active worker succeeds."""
        result = await worker_service.perform_action("worker-001", WorkerAction.KILL)

        assert result.success is True
        assert result.worker_id == "worker-001"
        assert result.action == WorkerAction.KILL
        assert "killed immediately" in result.message.lower()

    async def test_kill_sets_worker_offline(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that kill action sets worker status to offline."""
        await worker_service.perform_action("worker-001", WorkerAction.KILL)

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.status == WorkerStatus.OFFLINE

    async def test_kill_clears_current_task(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that kill action clears current task information."""
        await worker_service.perform_action("worker-001", WorkerAction.KILL)

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.current_task_id is None
        assert worker.current_task_name is None
        assert worker.current_task_started_at is None

    async def test_kill_without_force_shows_warning(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that kill without force shows task loss warning."""
        result = await worker_service.perform_action("worker-001", WorkerAction.KILL, force=False)

        assert result.success is True
        assert "warning" in result.message.lower() or "may be lost" in result.message.lower()

    async def test_kill_with_force_no_warning(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that kill with force doesn't show warning."""
        result = await worker_service.perform_action("worker-001", WorkerAction.KILL, force=True)

        assert result.success is True
        assert "warning" not in result.message.lower()
        assert "may be lost" not in result.message.lower()

    async def test_kill_offline_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test kill of offline worker fails."""
        result = await worker_service.perform_action("worker-005", WorkerAction.KILL)

        assert result.success is False
        assert "already offline" in result.message.lower()

    async def test_kill_nonexistent_worker_fails(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test kill of non-existent worker fails."""
        result = await worker_service.perform_action("nonexistent", WorkerAction.KILL)

        assert result.success is False
        assert "not found" in result.message.lower()


# ============================================================================
# Tests: get_worker_logs()
# ============================================================================


class TestGetWorkerLogs:
    """Tests for WorkerService.get_worker_logs() method."""

    async def test_get_worker_logs_returns_logs(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test getting logs for an existing worker."""
        result = await worker_service.get_worker_logs("worker-001")

        assert result is not None
        assert result.worker_id == "worker-001"
        assert len(result.logs) > 0

    async def test_get_worker_logs_returns_none_for_nonexistent_worker(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test getting logs for non-existent worker returns None."""
        result = await worker_service.get_worker_logs("nonexistent")
        assert result is None

    async def test_get_worker_logs_respects_limit(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that logs are limited by the limit parameter."""
        result = await worker_service.get_worker_logs("worker-001", limit=5)

        assert result is not None
        assert len(result.logs) <= 5

    async def test_get_worker_logs_respects_offset(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that logs respect offset for pagination."""
        result_page1 = await worker_service.get_worker_logs("worker-001", limit=5, offset=0)
        result_page2 = await worker_service.get_worker_logs("worker-001", limit=5, offset=5)

        assert result_page1 is not None
        assert result_page2 is not None
        # Pages should have different logs
        if len(result_page1.logs) > 0 and len(result_page2.logs) > 0:
            assert result_page1.logs[0].timestamp != result_page2.logs[0].timestamp

    async def test_get_worker_logs_filters_by_level(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering logs by log level."""
        result = await worker_service.get_worker_logs("worker-001", level="ERROR")

        assert result is not None
        for log in result.logs:
            assert log.level == "ERROR"

    async def test_get_worker_logs_filters_by_level_case_insensitive(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that level filter is case insensitive."""
        result_upper = await worker_service.get_worker_logs("worker-001", level="INFO")
        result_lower = await worker_service.get_worker_logs("worker-001", level="info")

        assert result_upper is not None
        assert result_lower is not None
        assert len(result_upper.logs) == len(result_lower.logs)

    async def test_get_worker_logs_filters_by_search(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test filtering logs by search term."""
        result = await worker_service.get_worker_logs("worker-001", search="task")

        assert result is not None
        for log in result.logs:
            assert "task" in log.message.lower()

    async def test_get_worker_logs_search_is_case_insensitive(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that search filter is case insensitive."""
        result_upper = await worker_service.get_worker_logs("worker-001", search="REDIS")
        result_lower = await worker_service.get_worker_logs("worker-001", search="redis")

        assert result_upper is not None
        assert result_lower is not None
        assert len(result_upper.logs) == len(result_lower.logs)

    async def test_get_worker_logs_has_more_flag(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that has_more flag indicates more logs available."""
        result = await worker_service.get_worker_logs("worker-001", limit=5, offset=0)

        assert result is not None
        if result.total > 5:
            assert result.has_more is True

    async def test_get_worker_logs_total_count(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that total count reflects filtered results."""
        result_all = await worker_service.get_worker_logs("worker-001")
        result_error = await worker_service.get_worker_logs("worker-001", level="ERROR")

        assert result_all is not None
        assert result_error is not None
        assert result_error.total <= result_all.total

    async def test_get_worker_logs_combined_filters(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test applying level and search filters together."""
        result = await worker_service.get_worker_logs("worker-001", level="INFO", search="started")

        assert result is not None
        for log in result.logs:
            assert log.level == "INFO"
            assert "started" in log.message.lower()


# ============================================================================
# Tests: handle_heartbeat()
# ============================================================================


class TestHandleHeartbeat:
    """Tests for WorkerService.handle_heartbeat() method."""

    async def test_heartbeat_updates_existing_worker(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that heartbeat updates existing worker data."""
        request = HeartbeatRequest(
            worker_id="worker-001",
            status=WorkerStatus.ACTIVE,
            current_task_id="new-task-123",
            current_task_name="new_task",
            cpu_usage=75.0,
            memory_usage=80.0,
            memory_mb=800,
            tasks_processed=2000,
            tasks_failed=30,
        )

        result = await worker_service.handle_heartbeat(request)

        assert result.received is True
        assert result.timestamp is not None

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.current_task_id == "new-task-123"
        assert worker.current_task_name == "new_task"
        assert worker.cpu_usage == 75.0
        assert worker.memory_usage == 80.0
        assert worker.memory_mb == 800
        assert worker.tasks_processed == 2000
        assert worker.tasks_failed == 30

    async def test_heartbeat_registers_new_worker(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that heartbeat registers a new worker."""
        request = HeartbeatRequest(
            worker_id="new-worker-999",
            status=WorkerStatus.IDLE,
            cpu_usage=10.0,
            memory_usage=20.0,
            memory_mb=200,
            tasks_processed=0,
            tasks_failed=0,
        )

        result = await worker_service.handle_heartbeat(request)

        assert result.received is True

        worker = await worker_service.get_worker_by_id("new-worker-999")
        assert worker is not None
        assert worker.id == "new-worker-999"
        assert worker.status == WorkerStatus.IDLE

    async def test_heartbeat_updates_last_heartbeat_timestamp(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that heartbeat updates last_heartbeat timestamp."""
        worker_before = await worker_service.get_worker_by_id("worker-001")
        assert worker_before is not None
        old_heartbeat = worker_before.last_heartbeat

        request = HeartbeatRequest(
            worker_id="worker-001",
            status=WorkerStatus.ACTIVE,
            cpu_usage=50.0,
            memory_usage=50.0,
            memory_mb=500,
            tasks_processed=1600,
            tasks_failed=25,
        )

        await worker_service.handle_heartbeat(request)

        worker_after = await worker_service.get_worker_by_id("worker-001")
        assert worker_after is not None
        assert worker_after.last_heartbeat >= old_heartbeat

    async def test_heartbeat_returns_pending_pause_action(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that heartbeat returns should_pause when action pending."""
        # Set up pending pause action
        await worker_service.perform_action("worker-001", WorkerAction.PAUSE)

        request = HeartbeatRequest(
            worker_id="worker-001",
            status=WorkerStatus.ACTIVE,
            cpu_usage=50.0,
            memory_usage=50.0,
            memory_mb=500,
            tasks_processed=1600,
            tasks_failed=25,
        )

        result = await worker_service.handle_heartbeat(request)

        assert result.should_pause is True

    async def test_heartbeat_returns_pending_shutdown_action(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that heartbeat returns should_shutdown when action pending."""
        # Set up pending shutdown action
        await worker_service.perform_action("worker-001", WorkerAction.SHUTDOWN)

        request = HeartbeatRequest(
            worker_id="worker-001",
            status=WorkerStatus.ACTIVE,
            cpu_usage=50.0,
            memory_usage=50.0,
            memory_mb=500,
            tasks_processed=1600,
            tasks_failed=25,
        )

        result = await worker_service.handle_heartbeat(request)

        assert result.should_shutdown is True

    async def test_heartbeat_sets_current_task_started_at_on_new_task(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that starting a new task sets current_task_started_at."""
        # First clear current task
        worker = worker_service._workers["worker-003"]
        worker.current_task_id = None
        worker.current_task_started_at = None

        request = HeartbeatRequest(
            worker_id="worker-003",
            status=WorkerStatus.ACTIVE,
            current_task_id="task-xyz",
            current_task_name="process_data",
            cpu_usage=50.0,
            memory_usage=50.0,
            memory_mb=500,
            tasks_processed=500,
            tasks_failed=10,
        )

        await worker_service.handle_heartbeat(request)

        worker = await worker_service.get_worker_by_id("worker-003")
        assert worker is not None
        assert worker.current_task_started_at is not None

    async def test_heartbeat_clears_current_task_started_at_on_no_task(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that clearing current task clears current_task_started_at."""
        request = HeartbeatRequest(
            worker_id="worker-001",
            status=WorkerStatus.IDLE,
            current_task_id=None,
            current_task_name=None,
            cpu_usage=10.0,
            memory_usage=30.0,
            memory_mb=300,
            tasks_processed=1600,
            tasks_failed=25,
        )

        await worker_service.handle_heartbeat(request)

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.current_task_id is None
        assert worker.current_task_started_at is None

    async def test_heartbeat_for_new_worker_initializes_storage(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that new worker registration initializes logs and actions."""
        request = HeartbeatRequest(
            worker_id="brand-new-worker",
            status=WorkerStatus.IDLE,
            cpu_usage=10.0,
            memory_usage=20.0,
            memory_mb=200,
            tasks_processed=0,
            tasks_failed=0,
        )

        await worker_service.handle_heartbeat(request)

        assert "brand-new-worker" in worker_service._worker_logs
        assert "brand-new-worker" in worker_service._pending_actions
        assert worker_service._pending_actions["brand-new-worker"]["pause"] is False
        assert worker_service._pending_actions["brand-new-worker"]["shutdown"] is False


# ============================================================================
# Tests: mark_stale_workers_offline()
# ============================================================================


class TestMarkStaleWorkersOffline:
    """Tests for WorkerService.mark_stale_workers_offline() method."""

    async def test_marks_stale_worker_offline(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that workers with old heartbeats are marked offline."""
        # Make a worker stale by setting old heartbeat
        worker = worker_service._workers["worker-001"]
        worker.last_heartbeat = datetime.now(UTC) - timedelta(minutes=5)

        marked = await worker_service.mark_stale_workers_offline(timeout_seconds=120)

        assert "worker-001" in marked

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.status == WorkerStatus.OFFLINE

    async def test_does_not_mark_fresh_worker_offline(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that workers with recent heartbeats are not marked offline."""
        # Ensure worker has fresh heartbeat
        worker = worker_service._workers["worker-001"]
        worker.last_heartbeat = datetime.now(UTC) - timedelta(seconds=30)

        marked = await worker_service.mark_stale_workers_offline(timeout_seconds=120)

        assert "worker-001" not in marked

    async def test_clears_current_task_when_marking_offline(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that current task is cleared when worker goes offline."""
        # Make worker stale
        worker = worker_service._workers["worker-001"]
        worker.last_heartbeat = datetime.now(UTC) - timedelta(minutes=5)

        await worker_service.mark_stale_workers_offline(timeout_seconds=120)

        worker = await worker_service.get_worker_by_id("worker-001")
        assert worker is not None
        assert worker.current_task_id is None
        assert worker.current_task_name is None
        assert worker.current_task_started_at is None

    async def test_does_not_mark_already_offline_workers(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that already offline workers are not re-marked."""
        # worker-005 is already offline
        marked = await worker_service.mark_stale_workers_offline(timeout_seconds=120)

        assert "worker-005" not in marked

    async def test_returns_list_of_marked_worker_ids(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that method returns list of worker IDs that were marked."""
        # Make multiple workers stale
        for worker_id in ["worker-001", "worker-002"]:
            worker = worker_service._workers[worker_id]
            worker.last_heartbeat = datetime.now(UTC) - timedelta(minutes=5)

        marked = await worker_service.mark_stale_workers_offline(timeout_seconds=120)

        assert isinstance(marked, list)
        assert "worker-001" in marked
        assert "worker-002" in marked

    async def test_respects_custom_timeout(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that custom timeout is respected."""
        # Set heartbeat to 3 minutes ago
        worker = worker_service._workers["worker-001"]
        worker.last_heartbeat = datetime.now(UTC) - timedelta(minutes=3)

        # With 120 second timeout (2 min), should be marked
        marked_short = await worker_service.mark_stale_workers_offline(timeout_seconds=120)

        # Re-initialize service
        worker_service2 = WorkerService()
        worker2 = worker_service2._workers["worker-001"]
        worker2.last_heartbeat = datetime.now(UTC) - timedelta(minutes=3)

        # With 300 second timeout (5 min), should NOT be marked
        marked_long = await worker_service2.mark_stale_workers_offline(timeout_seconds=300)

        assert "worker-001" in marked_short
        assert "worker-001" not in marked_long


# ============================================================================
# Tests: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_get_workers_with_empty_filters(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test get_workers with empty WorkerFilters object."""
        filters = WorkerFilters()
        result = await worker_service.get_workers(filters)

        assert result.total == len(worker_service._workers)

    async def test_search_with_special_characters(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test search filter with special characters."""
        filters = WorkerFilters(search="prod-01.example")
        result = await worker_service.get_workers(filters)

        # Should not raise, even if no matches
        assert isinstance(result.total, int)

    async def test_logs_pagination_beyond_total(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test requesting logs with offset beyond total."""
        result = await worker_service.get_worker_logs("worker-001", limit=10, offset=1000)

        assert result is not None
        assert len(result.logs) == 0
        assert result.has_more is False

    async def test_worker_action_response_contains_all_fields(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that action response contains all required fields."""
        result = await worker_service.perform_action("worker-001", WorkerAction.PAUSE)

        assert hasattr(result, "success")
        assert hasattr(result, "worker_id")
        assert hasattr(result, "action")
        assert hasattr(result, "message")

    async def test_heartbeat_response_contains_all_fields(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test that heartbeat response contains all required fields."""
        request = HeartbeatRequest(
            worker_id="worker-001",
            status=WorkerStatus.ACTIVE,
            cpu_usage=50.0,
            memory_usage=50.0,
            memory_mb=500,
            tasks_processed=1600,
            tasks_failed=25,
        )

        result = await worker_service.handle_heartbeat(request)

        assert hasattr(result, "received")
        assert hasattr(result, "timestamp")
        assert hasattr(result, "should_pause")
        assert hasattr(result, "should_shutdown")


# ============================================================================
# Tests: Worker Properties and Computed Fields (via service)
# ============================================================================


class TestWorkerPropertiesViaService:
    """Test that workers returned by service have correct computed properties."""

    async def test_worker_is_online_property(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test is_online computed property through service."""
        active_worker = await worker_service.get_worker_by_id("worker-001")
        offline_worker = await worker_service.get_worker_by_id("worker-005")

        assert active_worker is not None
        assert active_worker.is_online is True

        assert offline_worker is not None
        assert offline_worker.is_online is False

    async def test_worker_is_processing_property(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test is_processing computed property through service."""
        processing_worker = await worker_service.get_worker_by_id("worker-001")
        idle_worker = await worker_service.get_worker_by_id("worker-003")

        assert processing_worker is not None
        assert processing_worker.is_processing is True

        assert idle_worker is not None
        assert idle_worker.is_processing is False

    async def test_worker_success_rate_property(
        self,
        worker_service: WorkerService,
    ) -> None:
        """Test success_rate computed property through service."""
        worker = await worker_service.get_worker_by_id("worker-001")

        assert worker is not None
        assert 0 <= worker.success_rate <= 100
