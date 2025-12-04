"""Pytest configuration and shared fixtures.

This module follows pytest best practices:
- Use pytest-asyncio with strict mode for async tests
- Use factory fixtures for customizable test data
- Use dependency_overrides pattern for FastAPI testing
- Provide both sync and async client fixtures
"""

from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from starlette.testclient import TestClient

from asynctasq_monitor.api.dependencies import (
    get_queue_service,
    get_task_service,
    get_worker_service,
)
from asynctasq_monitor.api.main import create_monitoring_app
from asynctasq_monitor.config import Settings, get_settings
from asynctasq_monitor.models.queue import (
    Queue,
    QueueActionResponse,
    QueueClearResponse,
    QueueFilters,
    QueueListResponse,
    QueueMetrics,
    QueueStatus,
)
from asynctasq_monitor.models.task import Task, TaskFilters, TaskStatus
from asynctasq_monitor.models.worker import (
    HeartbeatRequest,
    HeartbeatResponse,
    Worker,
    WorkerAction,
    WorkerActionResponse,
    WorkerDetail,
    WorkerFilters,
    WorkerListResponse,
    WorkerLog,
    WorkerLogsResponse,
    WorkerStatus,
)

# ============================================================================
# Mock Service
# ============================================================================


class MockTaskService:
    """Mock TaskService for testing without actual queue backend."""

    def __init__(self, *, tasks: list[Task] | None = None) -> None:
        """Initialize with optional list of tasks."""
        self._tasks = list(tasks) if tasks else []

    async def get_tasks(
        self,
        filters: TaskFilters,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Return filtered and paginated tasks."""
        items = self._tasks

        if filters.status is not None:
            items = [t for t in items if t.status == filters.status]
        if filters.queue is not None:
            items = [t for t in items if t.queue == filters.queue]
        if filters.worker_id is not None:
            items = [t for t in items if t.worker_id == filters.worker_id]
        if filters.search is not None:
            search_lower = filters.search.lower()
            items = [
                t for t in items if search_lower in t.name.lower() or search_lower in t.id.lower()
            ]
        if filters.tags is not None:
            items = [t for t in items if any(tag in t.tags for tag in filters.tags)]

        total = len(items)
        return items[offset : offset + limit], total

    async def get_task_by_id(self, task_id: str) -> Task | None:
        """Return a task by ID or None if not found."""
        for t in self._tasks:
            if t.id == task_id:
                return t
        return None

    async def retry_task(self, task_id: str) -> bool:
        """Attempt to retry a failed task."""
        task = await self.get_task_by_id(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        # In real implementation this would re-enqueue
        return True

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        for i, t in enumerate(self._tasks):
            if t.id == task_id:
                del self._tasks[i]
                return True
        return False

    def add_task(self, task: Task) -> None:
        """Add a task to the mock store (for test setup)."""
        self._tasks.append(task)

    def clear(self) -> None:
        """Clear all tasks (for test cleanup)."""
        self._tasks.clear()


class MockWorkerService:
    """Mock WorkerService for testing without actual queue backend."""

    def __init__(self, *, workers: list[Worker] | None = None) -> None:
        """Initialize with optional list of workers."""
        self._workers: dict[str, Worker] = {}
        self._logs: dict[str, list[WorkerLog]] = {}
        self._pending_actions: dict[str, dict[str, bool]] = {}
        if workers:
            for w in workers:
                self._workers[w.id] = w
                self._logs[w.id] = []
                self._pending_actions[w.id] = {"pause": False, "shutdown": False}

    async def get_workers(
        self,
        filters: WorkerFilters | None = None,
    ) -> WorkerListResponse:
        """Return filtered workers as WorkerListResponse."""

        items = list(self._workers.values())

        if filters:
            if filters.status is not None:
                items = [w for w in items if w.status == filters.status]
            if filters.queue is not None:
                items = [w for w in items if filters.queue in w.queues]
            if filters.search is not None:
                search_lower = filters.search.lower()
                items = [
                    w
                    for w in items
                    if search_lower in w.name.lower()
                    or search_lower in w.id.lower()
                    or (w.hostname and search_lower in w.hostname.lower())
                ]
            if filters.is_paused is not None:
                items = [w for w in items if w.is_paused == filters.is_paused]
            if filters.has_current_task is not None:
                if filters.has_current_task:
                    items = [w for w in items if w.current_task_id is not None]
                else:
                    items = [w for w in items if w.current_task_id is None]

        return WorkerListResponse(items=items, total=len(items))

    async def get_worker_by_id(self, worker_id: str) -> Worker | None:
        """Return a worker by ID or None if not found."""
        return self._workers.get(worker_id)

    async def get_worker_detail(self, worker_id: str) -> WorkerDetail | None:
        """Return detailed worker info or None if not found."""

        worker = self._workers.get(worker_id)
        if worker is None:
            return None
        return WorkerDetail(**worker.model_dump(), recent_tasks=[], hourly_throughput=[])

    async def perform_action(
        self,
        worker_id: str,
        action: WorkerAction,
        *,
        force: bool = False,
    ) -> WorkerActionResponse:
        """Perform a management action on a worker."""
        worker = self._workers.get(worker_id)
        if not worker:
            return WorkerActionResponse(
                success=False,
                worker_id=worker_id,
                action=action,
                message=f"Worker {worker_id} not found",
            )

        if action == WorkerAction.PAUSE:
            if worker.status == WorkerStatus.OFFLINE:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Cannot pause offline worker",
                )
            if worker.is_paused:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Worker is already paused",
                )
            self._workers[worker_id] = worker.model_copy(update={"is_paused": True})
            return WorkerActionResponse(
                success=True,
                worker_id=worker_id,
                action=action,
                message=f"Worker {worker_id} paused - will stop accepting new tasks",
            )

        if action == WorkerAction.RESUME:
            if not worker.is_paused:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Worker is not paused",
                )
            self._workers[worker_id] = worker.model_copy(update={"is_paused": False})
            return WorkerActionResponse(
                success=True,
                worker_id=worker_id,
                action=action,
                message=f"Worker {worker_id} resumed",
            )

        if action == WorkerAction.SHUTDOWN:
            if worker.status == WorkerStatus.OFFLINE:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Worker is already offline",
                )
            return WorkerActionResponse(
                success=True,
                worker_id=worker_id,
                action=action,
                message=f"Worker {worker_id} will shutdown after current task",
            )

        if action == WorkerAction.KILL:
            if worker.status == WorkerStatus.OFFLINE:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Worker is already offline",
                )
            self._workers[worker_id] = worker.model_copy(
                update={
                    "status": WorkerStatus.OFFLINE,
                    "current_task_id": None,
                    "current_task_name": None,
                    "current_task_started_at": None,
                }
            )
            return WorkerActionResponse(
                success=True,
                worker_id=worker_id,
                action=action,
                message=f"Worker {worker_id} killed immediately",
            )

        return WorkerActionResponse(
            success=False,
            worker_id=worker_id,
            action=action,
            message=f"Unknown action: {action}",
        )

    async def get_worker_logs(
        self,
        worker_id: str,
        *,
        level: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> WorkerLogsResponse | None:
        """Get logs for a specific worker."""
        if worker_id not in self._workers:
            return None

        now = datetime.now(UTC)
        logs = [
            WorkerLog(
                timestamp=now - timedelta(seconds=i * 30),
                level=["INFO", "DEBUG", "WARNING", "ERROR"][i % 4],
                message=f"Log message {i}",
                logger_name="asynctasq.worker",
            )
            for i in range(20)
        ]

        if level:
            logs = [log for log in logs if log.level == level.upper()]
        if search:
            logs = [log for log in logs if search.lower() in log.message.lower()]

        total = len(logs)
        logs = logs[offset : offset + limit]

        return WorkerLogsResponse(
            worker_id=worker_id,
            logs=logs,
            total=total,
            has_more=offset + len(logs) < total,
        )

    async def handle_heartbeat(self, request: HeartbeatRequest) -> HeartbeatResponse:
        """Process a heartbeat from a worker."""
        now = datetime.now(UTC)
        worker_id = request.worker_id
        actions = self._pending_actions.get(worker_id, {})

        return HeartbeatResponse(
            received=True,
            timestamp=now,
            should_pause=actions.get("pause", False),
            should_shutdown=actions.get("shutdown", False),
        )

    def add_worker(self, worker: Worker) -> None:
        """Add a worker to the mock store (for test setup)."""
        self._workers[worker.id] = worker
        self._logs[worker.id] = []
        self._pending_actions[worker.id] = {"pause": False, "shutdown": False}

    def add_logs(self, worker_id: str, logs: list[WorkerLog]) -> None:
        """Add logs for a worker (for test setup)."""
        self._logs[worker_id] = logs

    def clear(self) -> None:
        """Clear all workers (for test cleanup)."""
        self._workers.clear()
        self._logs.clear()
        self._pending_actions.clear()


class MockQueueService:
    """Mock QueueService for testing without actual queue backend."""

    def __init__(self, *, queues: list[Queue] | None = None) -> None:
        """Initialize with optional list of queues."""
        self._queues: dict[str, Queue] = {}
        self._metrics: dict[str, list[QueueMetrics]] = {}
        if queues:
            for q in queues:
                self._queues[q.name] = q
                self._metrics[q.name] = []

    async def get_queues(
        self,
        filters: QueueFilters | None = None,
    ) -> QueueListResponse:
        """Return filtered queues as QueueListResponse."""
        items = list(self._queues.values())

        if filters:
            if filters.status is not None:
                items = [q for q in items if q.status == filters.status]
            if filters.search is not None:
                search_lower = filters.search.lower()
                items = [q for q in items if search_lower in q.name.lower()]
            if filters.min_depth is not None:
                items = [q for q in items if q.depth >= filters.min_depth]
            if filters.alert_level is not None:
                items = [q for q in items if q.alert_level == filters.alert_level]

        return QueueListResponse(items=items, total=len(items))

    async def get_queue_by_name(self, queue_name: str) -> Queue | None:
        """Return a queue by name or None if not found."""
        return self._queues.get(queue_name)

    async def pause_queue(self, queue_name: str, reason: str | None = None) -> QueueActionResponse:
        """Pause a queue."""
        queue = self._queues.get(queue_name)
        if queue is None:
            return QueueActionResponse(
                success=False,
                queue_name=queue_name,
                action="pause",
                message=f"Queue '{queue_name}' not found",
            )

        if queue.status == QueueStatus.PAUSED:
            return QueueActionResponse(
                success=False,
                queue_name=queue_name,
                action="pause",
                message=f"Queue '{queue_name}' is already paused",
            )

        # Update queue status
        self._queues[queue_name] = Queue(
            name=queue.name,
            status=QueueStatus.PAUSED,
            depth=queue.depth,
            processing=queue.processing,
            completed_total=queue.completed_total,
            failed_total=queue.failed_total,
            workers_assigned=queue.workers_assigned,
            avg_duration_ms=queue.avg_duration_ms,
            throughput_per_minute=queue.throughput_per_minute,
            priority=queue.priority,
            max_retries=queue.max_retries,
            created_at=queue.created_at,
            paused_at=datetime.now(UTC),
        )

        return QueueActionResponse(
            success=True,
            queue_name=queue_name,
            action="pause",
            message=f"Queue '{queue_name}' paused successfully"
            + (f" - Reason: {reason}" if reason else ""),
        )

    async def resume_queue(self, queue_name: str) -> QueueActionResponse:
        """Resume a paused queue."""
        queue = self._queues.get(queue_name)
        if queue is None:
            return QueueActionResponse(
                success=False,
                queue_name=queue_name,
                action="resume",
                message=f"Queue '{queue_name}' not found",
            )

        if queue.status != QueueStatus.PAUSED:
            return QueueActionResponse(
                success=False,
                queue_name=queue_name,
                action="resume",
                message=f"Queue '{queue_name}' is not paused",
            )

        # Update queue status
        self._queues[queue_name] = Queue(
            name=queue.name,
            status=QueueStatus.ACTIVE,
            depth=queue.depth,
            processing=queue.processing,
            completed_total=queue.completed_total,
            failed_total=queue.failed_total,
            workers_assigned=queue.workers_assigned,
            avg_duration_ms=queue.avg_duration_ms,
            throughput_per_minute=queue.throughput_per_minute,
            priority=queue.priority,
            max_retries=queue.max_retries,
            created_at=queue.created_at,
            paused_at=None,
        )

        return QueueActionResponse(
            success=True,
            queue_name=queue_name,
            action="resume",
            message=f"Queue '{queue_name}' resumed successfully",
        )

    async def clear_queue(self, queue_name: str) -> QueueClearResponse:
        """Clear all pending tasks from a queue."""
        queue = self._queues.get(queue_name)
        if queue is None:
            return QueueClearResponse(
                success=False,
                queue_name=queue_name,
                tasks_cleared=0,
                message=f"Queue '{queue_name}' not found",
            )

        pending_count = queue.depth

        # Update queue with cleared depth
        self._queues[queue_name] = Queue(
            name=queue.name,
            status=queue.status,
            depth=0,
            processing=queue.processing,
            completed_total=queue.completed_total,
            failed_total=queue.failed_total,
            workers_assigned=queue.workers_assigned,
            avg_duration_ms=queue.avg_duration_ms,
            throughput_per_minute=queue.throughput_per_minute,
            priority=queue.priority,
            max_retries=queue.max_retries,
            created_at=queue.created_at,
            paused_at=queue.paused_at,
        )

        return QueueClearResponse(
            success=True,
            queue_name=queue_name,
            tasks_cleared=pending_count,
            message=f"Cleared {pending_count} tasks from queue '{queue_name}'",
        )

    async def get_queue_metrics(
        self,
        queue_name: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        interval_minutes: int = 5,
    ) -> list[QueueMetrics]:
        """Get historical metrics for a queue."""
        _ = from_time, to_time, interval_minutes
        return self._metrics.get(queue_name, [])

    def add_queue(self, queue: Queue) -> None:
        """Add a queue to the mock store (for test setup)."""
        self._queues[queue.name] = queue
        self._metrics[queue.name] = []

    def add_metrics(self, queue_name: str, metrics: list[QueueMetrics]) -> None:
        """Add metrics for a queue (for test setup)."""
        self._metrics[queue_name] = metrics

    def clear(self) -> None:
        """Clear all queues (for test cleanup)."""
        self._queues.clear()
        self._metrics.clear()


# ============================================================================
# Factory Fixtures
# ============================================================================


@pytest.fixture
def task_factory() -> Callable[..., Task]:
    """Factory fixture for creating Task instances with customizable fields.

    Example:
        def test_something(task_factory):
            task = task_factory(name="my-task", status=TaskStatus.FAILED)
            assert task.status == TaskStatus.FAILED
    """

    def _create_task(
        *,
        id: str | None = None,
        name: str = "test-task",
        queue: str = "default",
        status: TaskStatus = TaskStatus.PENDING,
        enqueued_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_ms: int | None = None,
        worker_id: str | None = None,
        attempt: int = 1,
        max_retries: int = 3,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        result: Any | None = None,
        exception: str | None = None,
        traceback: str | None = None,
        priority: int = 0,
        timeout_seconds: int | None = None,
        tags: list[str] | None = None,
    ) -> Task:
        return Task(
            id=id or str(uuid4()),
            name=name,
            queue=queue,
            status=status,
            enqueued_at=enqueued_at or datetime.now(UTC),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            worker_id=worker_id,
            attempt=attempt,
            max_retries=max_retries,
            args=args or [],
            kwargs=kwargs or {},
            result=result,
            exception=exception,
            traceback=traceback,
            priority=priority,
            timeout_seconds=timeout_seconds,
            tags=tags or [],
        )

    return _create_task


@pytest.fixture
def sample_tasks(task_factory: Callable[..., Task]) -> list[Task]:
    """Generate a set of sample tasks for testing."""
    now = datetime.now(UTC)
    return [
        task_factory(
            id="t1",
            name="send-email",
            status=TaskStatus.PENDING,
            queue="emails",
            enqueued_at=now,
            priority=1,
            tags=["transactional"],
        ),
        task_factory(
            id="t2",
            name="process-payment",
            status=TaskStatus.FAILED,
            queue="payments",
            enqueued_at=now - timedelta(minutes=5),
            started_at=now - timedelta(minutes=4),
            completed_at=now - timedelta(minutes=3),
            duration_ms=60000,
            worker_id="worker-1",
            attempt=3,
            exception="PaymentGatewayError: Connection timeout",
            traceback="Traceback (most recent call last):\n  ...",
            tags=["critical"],
        ),
        task_factory(
            id="t3",
            name="generate-report",
            status=TaskStatus.COMPLETED,
            queue="reports",
            enqueued_at=now - timedelta(hours=1),
            started_at=now - timedelta(minutes=50),
            completed_at=now - timedelta(minutes=45),
            duration_ms=300000,
            worker_id="worker-2",
            result={"report_url": "https://example.com/report.pdf"},
        ),
        task_factory(
            id="t4",
            name="send-notification",
            status=TaskStatus.RUNNING,
            queue="notifications",
            enqueued_at=now - timedelta(seconds=30),
            started_at=now - timedelta(seconds=10),
            worker_id="worker-1",
        ),
    ]


@pytest.fixture
def worker_factory() -> Callable[..., Worker]:
    """Factory fixture for creating Worker instances with customizable fields.

    Example:
        def test_something(worker_factory):
            worker = worker_factory(name="worker-1", status=WorkerStatus.IDLE)
            assert worker.status == WorkerStatus.IDLE
    """

    def _create_worker(
        *,
        id: str | None = None,
        name: str = "test-worker",
        hostname: str | None = "test-host",
        pid: int | None = 1234,
        status: WorkerStatus = WorkerStatus.ACTIVE,
        queues: list[str] | None = None,
        current_task_id: str | None = None,
        current_task_name: str | None = None,
        current_task_started_at: datetime | None = None,
        tasks_processed: int = 0,
        tasks_failed: int = 0,
        avg_task_duration_ms: float | None = None,
        uptime_seconds: int = 3600,
        started_at: datetime | None = None,
        last_heartbeat: datetime | None = None,
        cpu_usage: float | None = 25.0,
        memory_usage: float | None = 50.0,
        memory_mb: int | None = 512,
        version: str | None = "1.0.0",
        tags: list[str] | None = None,
        is_paused: bool = False,
    ) -> Worker:
        now = datetime.now(UTC)
        return Worker(
            id=id or f"worker-{uuid4().hex[:8]}",
            name=name,
            hostname=hostname,
            pid=pid,
            status=status,
            queues=queues or ["default"],
            current_task_id=current_task_id,
            current_task_name=current_task_name,
            current_task_started_at=current_task_started_at,
            tasks_processed=tasks_processed,
            tasks_failed=tasks_failed,
            avg_task_duration_ms=avg_task_duration_ms,
            uptime_seconds=uptime_seconds,
            started_at=started_at or (now - timedelta(seconds=uptime_seconds)),
            last_heartbeat=last_heartbeat or now,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            memory_mb=memory_mb,
            version=version,
            tags=tags or [],
            is_paused=is_paused,
        )

    return _create_worker


@pytest.fixture
def sample_workers(worker_factory: Callable[..., Worker]) -> list[Worker]:
    """Generate a set of sample workers for testing."""
    now = datetime.now(UTC)
    return [
        worker_factory(
            id="worker-1",
            name="email-worker",
            hostname="prod-worker-01",
            status=WorkerStatus.ACTIVE,
            queues=["emails", "notifications"],
            current_task_id="task-abc",
            current_task_name="send-email",
            current_task_started_at=now - timedelta(seconds=5),
            tasks_processed=1500,
            tasks_failed=12,
            cpu_usage=45.2,
            memory_usage=62.5,
        ),
        worker_factory(
            id="worker-2",
            name="payment-worker",
            hostname="prod-worker-02",
            status=WorkerStatus.IDLE,
            queues=["payments"],
            tasks_processed=500,
            tasks_failed=3,
            cpu_usage=5.0,
            memory_usage=30.0,
            is_paused=True,
        ),
        worker_factory(
            id="worker-3",
            name="report-worker",
            hostname="prod-worker-03",
            status=WorkerStatus.OFFLINE,
            queues=["reports"],
            tasks_processed=100,
            tasks_failed=1,
            last_heartbeat=now - timedelta(minutes=5),
        ),
    ]


@pytest.fixture
def queue_factory() -> Callable[..., Queue]:
    """Factory fixture for creating Queue instances with customizable fields.

    Example:
        def test_something(queue_factory):
            queue = queue_factory(name="my-queue", status=QueueStatus.PAUSED)
            assert queue.status == QueueStatus.PAUSED
    """

    def _create_queue(
        *,
        name: str = "test-queue",
        status: QueueStatus = QueueStatus.ACTIVE,
        depth: int = 0,
        processing: int = 0,
        completed_total: int = 0,
        failed_total: int = 0,
        workers_assigned: int = 0,
        avg_duration_ms: float | None = None,
        throughput_per_minute: float | None = None,
        priority: int = 0,
        max_retries: int = 3,
        created_at: datetime | None = None,
        paused_at: datetime | None = None,
    ) -> Queue:
        return Queue(
            name=name,
            status=status,
            depth=depth,
            processing=processing,
            completed_total=completed_total,
            failed_total=failed_total,
            workers_assigned=workers_assigned,
            avg_duration_ms=avg_duration_ms,
            throughput_per_minute=throughput_per_minute,
            priority=priority,
            max_retries=max_retries,
            created_at=created_at,
            paused_at=paused_at,
        )

    return _create_queue


@pytest.fixture
def sample_queues(queue_factory: Callable[..., Queue]) -> list[Queue]:
    """Generate a set of sample queues for testing."""
    now = datetime.now(UTC)
    return [
        queue_factory(
            name="emails",
            status=QueueStatus.ACTIVE,
            depth=42,
            processing=5,
            completed_total=15000,
            failed_total=150,
            workers_assigned=3,
            avg_duration_ms=1250.5,
            throughput_per_minute=45.2,
            priority=1,
            created_at=now - timedelta(days=30),
        ),
        queue_factory(
            name="payments",
            status=QueueStatus.PAUSED,
            depth=15,
            processing=0,
            completed_total=5000,
            failed_total=50,
            workers_assigned=0,
            avg_duration_ms=2500.0,
            throughput_per_minute=0.0,
            priority=2,
            created_at=now - timedelta(days=30),
            paused_at=now - timedelta(hours=2),
        ),
        queue_factory(
            name="reports",
            status=QueueStatus.ACTIVE,
            depth=150,  # Warning level (>100)
            processing=2,
            completed_total=1000,
            failed_total=25,
            workers_assigned=1,
            avg_duration_ms=30000.0,
            throughput_per_minute=2.5,
            priority=0,
            created_at=now - timedelta(days=15),
        ),
        queue_factory(
            name="notifications",
            status=QueueStatus.ACTIVE,
            depth=550,  # Critical level (>500)
            processing=10,
            completed_total=50000,
            failed_total=500,
            workers_assigned=5,
            avg_duration_ms=500.0,
            throughput_per_minute=120.0,
            priority=0,
            created_at=now - timedelta(days=60),
        ),
    ]


# ============================================================================
# Service Fixtures
# ============================================================================


@pytest.fixture
def mock_task_service(sample_tasks: list[Task]) -> MockTaskService:
    """Create a MockTaskService populated with sample tasks."""
    return MockTaskService(tasks=sample_tasks)


@pytest.fixture
def empty_mock_task_service() -> MockTaskService:
    """Create an empty MockTaskService for testing empty states."""
    return MockTaskService()


@pytest.fixture
def mock_worker_service(sample_workers: list[Worker]) -> MockWorkerService:
    """Create a MockWorkerService populated with sample workers."""
    return MockWorkerService(workers=sample_workers)


@pytest.fixture
def empty_mock_worker_service() -> MockWorkerService:
    """Create an empty MockWorkerService for testing empty states."""
    return MockWorkerService()


@pytest.fixture
def mock_queue_service(sample_queues: list[Queue]) -> MockQueueService:
    """Create a MockQueueService populated with sample queues."""
    return MockQueueService(queues=sample_queues)


@pytest.fixture
def empty_mock_queue_service() -> MockQueueService:
    """Create an empty MockQueueService for testing empty states."""
    return MockQueueService()


@pytest.fixture
def test_settings() -> Settings:
    """Create test-specific settings."""
    return Settings(
        debug=True,
        host="127.0.0.1",
        port=8080,
        cors_origins=["http://localhost:3000"],
        enable_auth=False,
        secret_key="test-secret-key-for-testing-only",
        polling_interval_seconds=1,
        log_level="DEBUG",
    )


# ============================================================================
# App & Client Fixtures
# ============================================================================


@pytest.fixture
def app(
    mock_task_service: MockTaskService,
    mock_worker_service: MockWorkerService,
    mock_queue_service: MockQueueService,
    test_settings: Settings,
) -> FastAPI:
    """Create a FastAPI app with mocked dependencies."""
    app: FastAPI = create_monitoring_app()

    async def _override_get_task_service() -> MockTaskService:
        return mock_task_service

    async def _override_get_worker_service() -> MockWorkerService:
        return mock_worker_service

    async def _override_get_queue_service() -> MockQueueService:
        return mock_queue_service

    def _override_get_settings() -> Settings:
        return test_settings

    app.dependency_overrides[get_task_service] = _override_get_task_service
    app.dependency_overrides[get_worker_service] = _override_get_worker_service
    app.dependency_overrides[get_queue_service] = _override_get_queue_service
    app.dependency_overrides[get_settings] = _override_get_settings

    return app


@pytest.fixture
def sync_client(app: FastAPI) -> Iterator[TestClient]:
    """Synchronous test client for non-async tests.

    Example:
        def test_health(sync_client):
            response = sync_client.get("/api/")
            assert response.status_code == 200
    """
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Async test client for async tests.

    Example:
        @pytest.mark.asyncio
        async def test_health(async_client):
            response = await async_client.get("/api/")
            assert response.status_code == 200
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as client:
        yield client


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers and helpers."""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )

    # Load test helpers module
    import importlib.util
    from pathlib import Path

    helpers_path = Path(__file__).parent / "_helpers.py"
    if helpers_path.exists():
        spec = importlib.util.spec_from_file_location("test_helpers", helpers_path)
        if spec is not None and spec.loader is not None:
            _helpers = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_helpers)  # type: ignore[arg-type]

            # Assign helpers to pytest namespace
            if not hasattr(pytest, "helpers"):
                pytest.helpers = _helpers  # type: ignore[attr-defined]


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Modify test collection to auto-mark async tests."""
    import inspect

    for item in items:
        # Auto-add asyncio marker to async test functions
        if isinstance(item, pytest.Function):
            if inspect.iscoroutinefunction(item.obj):
                item.add_marker(pytest.mark.asyncio)
