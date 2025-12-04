"""Worker service for managing and monitoring workers.

This module provides the service layer for worker operations following
FastAPI/Python best practices:
- Async/await throughout for non-blocking I/O
- Type hints with modern Python 3.11+ syntax
- Clean separation from route handlers
- Dependency injection ready

In a production system, this would integrate with the actual queue
driver (Redis, RabbitMQ, etc.) to fetch worker data. For now, it
provides a mock implementation for development and testing.
"""

from datetime import UTC, datetime, timedelta

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
    WorkerTask,
)


class WorkerService:
    """Service for worker monitoring and management operations.

    This service provides a unified interface for:
    - Fetching worker status and statistics
    - Managing workers (pause, resume, shutdown, kill)
    - Handling worker heartbeats
    - Streaming worker logs

    In production, this would delegate to the actual queue driver.
    For development, it uses an in-memory store with mock data.
    """

    def __init__(self) -> None:
        """Initialize the worker service with mock data."""
        self._workers: dict[str, Worker] = {}
        self._worker_logs: dict[str, list[WorkerLog]] = {}
        self._pending_actions: dict[str, dict[str, bool]] = {}
        self._initialize_mock_data()

    def _initialize_mock_data(self) -> None:
        """Initialize with sample workers for development."""
        now = datetime.now(UTC)
        mock_workers = [
            Worker(
                id="worker-001",
                name="worker-prod-01",
                hostname="server-01.example.com",
                pid=12345,
                status=WorkerStatus.ACTIVE,
                queues=["default", "high", "emails"],
                current_task_id="task-abc-123",
                current_task_name="send_email",
                current_task_started_at=now - timedelta(seconds=5),
                tasks_processed=1542,
                tasks_failed=23,
                avg_task_duration_ms=1850.5,
                uptime_seconds=86400,
                started_at=now - timedelta(days=1),
                last_heartbeat=now - timedelta(seconds=10),
                cpu_usage=45.5,
                memory_usage=62.3,
                memory_mb=512,
                version="1.0.0",
                tags=["production", "primary"],
            ),
            Worker(
                id="worker-002",
                name="worker-prod-02",
                hostname="server-02.example.com",
                pid=12346,
                status=WorkerStatus.ACTIVE,
                queues=["default", "payments"],
                current_task_id="task-def-456",
                current_task_name="process_payment",
                current_task_started_at=now - timedelta(seconds=12),
                tasks_processed=892,
                tasks_failed=15,
                avg_task_duration_ms=2450.0,
                uptime_seconds=43200,
                started_at=now - timedelta(hours=12),
                last_heartbeat=now - timedelta(seconds=5),
                cpu_usage=78.2,
                memory_usage=71.0,
                memory_mb=640,
                version="1.0.0",
                tags=["production"],
            ),
            Worker(
                id="worker-003",
                name="worker-prod-03",
                hostname="server-03.example.com",
                pid=12347,
                status=WorkerStatus.IDLE,
                queues=["default", "low"],
                tasks_processed=456,
                tasks_failed=8,
                avg_task_duration_ms=950.0,
                uptime_seconds=172800,
                started_at=now - timedelta(days=2),
                last_heartbeat=now - timedelta(seconds=15),
                cpu_usage=5.0,
                memory_usage=35.0,
                memory_mb=280,
                version="1.0.0",
                tags=["production"],
            ),
            Worker(
                id="worker-004",
                name="worker-staging-01",
                hostname="staging-01.example.com",
                pid=5678,
                status=WorkerStatus.ACTIVE,
                queues=["staging"],
                current_task_id="task-ghi-789",
                current_task_name="generate_report",
                current_task_started_at=now - timedelta(seconds=30),
                tasks_processed=234,
                tasks_failed=5,
                avg_task_duration_ms=5200.0,
                uptime_seconds=7200,
                started_at=now - timedelta(hours=2),
                last_heartbeat=now - timedelta(seconds=8),
                cpu_usage=92.0,
                memory_usage=85.0,
                memory_mb=720,
                version="1.0.1-beta",
                tags=["staging"],
            ),
            Worker(
                id="worker-005",
                name="worker-prod-04",
                hostname="server-04.example.com",
                pid=12348,
                status=WorkerStatus.OFFLINE,
                queues=["default"],
                tasks_processed=2100,
                tasks_failed=45,
                avg_task_duration_ms=1200.0,
                uptime_seconds=0,
                started_at=now - timedelta(days=5),
                last_heartbeat=now - timedelta(minutes=10),
                version="0.9.5",
                tags=["production", "deprecated"],
            ),
        ]

        for worker in mock_workers:
            self._workers[worker.id] = worker
            self._worker_logs[worker.id] = []
            self._pending_actions[worker.id] = {"pause": False, "shutdown": False}

    async def get_workers(
        self,
        filters: WorkerFilters | None = None,
    ) -> WorkerListResponse:
        """Get all workers with optional filtering.

        Args:
            filters: Optional filters to apply to the worker list.

        Returns:
            WorkerListResponse containing filtered workers and counts.
        """
        workers = list(self._workers.values())

        if filters is not None:
            if filters.status is not None:
                workers = [w for w in workers if w.status == filters.status]

            if filters.queue is not None:
                workers = [w for w in workers if filters.queue in w.queues]

            if filters.search is not None:
                search_lower = filters.search.lower()
                workers = [
                    w
                    for w in workers
                    if search_lower in w.name.lower()
                    or search_lower in w.id.lower()
                    or (w.hostname and search_lower in w.hostname.lower())
                ]

            if filters.is_paused is not None:
                workers = [w for w in workers if w.is_paused == filters.is_paused]

            if filters.has_current_task is not None:
                if filters.has_current_task:
                    workers = [w for w in workers if w.current_task_id is not None]
                else:
                    workers = [w for w in workers if w.current_task_id is None]

        # Sort by status (active first) then by name
        status_order = {WorkerStatus.ACTIVE: 0, WorkerStatus.IDLE: 1, WorkerStatus.OFFLINE: 2}
        workers.sort(key=lambda w: (status_order.get(w.status, 3), w.name))

        return WorkerListResponse(items=workers, total=len(workers))

    async def get_worker_by_id(self, worker_id: str) -> Worker | None:
        """Get a single worker by ID.

        Args:
            worker_id: The unique worker identifier.

        Returns:
            Worker if found, None otherwise.
        """
        return self._workers.get(worker_id)

    async def get_worker_detail(self, worker_id: str) -> WorkerDetail | None:
        """Get detailed worker information including task history.

        Args:
            worker_id: The unique worker identifier.

        Returns:
            WorkerDetail with full history, None if not found.
        """
        worker = self._workers.get(worker_id)
        if worker is None:
            return None

        # Generate mock task history
        now = datetime.now(UTC)
        recent_tasks = [
            WorkerTask(
                id=f"task-{i}",
                name=name,
                queue=queue,
                status=status,
                started_at=now - timedelta(minutes=i * 5),
                completed_at=now - timedelta(minutes=i * 5 - 2) if status != "running" else None,
                duration_ms=int(1000 + i * 100) if status != "running" else None,
            )
            for i, (name, queue, status) in enumerate(
                [
                    ("send_email", "emails", "completed"),
                    ("process_payment", "payments", "completed"),
                    ("generate_report", "reports", "failed"),
                    ("cleanup_temp", "default", "completed"),
                    ("send_notification", "notifications", "completed"),
                    ("sync_data", "default", "completed"),
                    ("validate_order", "orders", "completed"),
                    ("resize_image", "media", "completed"),
                    ("calculate_stats", "analytics", "completed"),
                    ("export_csv", "exports", "completed"),
                ]
            )
        ]

        # Generate mock hourly throughput
        hourly_throughput = [
            {"hour": (now - timedelta(hours=i)).isoformat(), "count": 20 + i % 15}
            for i in range(24, 0, -1)
        ]

        return WorkerDetail(
            **worker.model_dump(),
            recent_tasks=recent_tasks,
            hourly_throughput=hourly_throughput,
        )

    async def perform_action(
        self,
        worker_id: str,
        action: WorkerAction,
        *,
        force: bool = False,
    ) -> WorkerActionResponse:
        """Perform a management action on a worker.

        Args:
            worker_id: The worker to act upon.
            action: The action to perform.
            force: Whether to force the action (skip confirmations).

        Returns:
            WorkerActionResponse with result status and message.

        Raises:
            ValueError: If worker not found or action not allowed.
        """
        worker = self._workers.get(worker_id)
        if worker is None:
            return WorkerActionResponse(
                success=False,
                worker_id=worker_id,
                action=action,
                message=f"Worker {worker_id} not found",
            )

        # Check if action is valid for current state
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
            # Mark worker as paused
            worker.is_paused = True
            self._pending_actions[worker_id]["pause"] = True
            message = f"Worker {worker_id} paused - will stop accepting new tasks"

        elif action == WorkerAction.RESUME:
            if not worker.is_paused:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Worker is not paused",
                )
            worker.is_paused = False
            self._pending_actions[worker_id]["pause"] = False
            message = f"Worker {worker_id} resumed"

        elif action == WorkerAction.SHUTDOWN:
            if worker.status == WorkerStatus.OFFLINE:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Worker is already offline",
                )
            self._pending_actions[worker_id]["shutdown"] = True
            message = f"Worker {worker_id} will shutdown after current task"

        elif action == WorkerAction.KILL:
            if worker.status == WorkerStatus.OFFLINE:
                return WorkerActionResponse(
                    success=False,
                    worker_id=worker_id,
                    action=action,
                    message="Worker is already offline",
                )
            # Immediately set offline (in production, would send SIGKILL)
            worker.status = WorkerStatus.OFFLINE
            worker.current_task_id = None
            worker.current_task_name = None
            worker.current_task_started_at = None
            message = f"Worker {worker_id} killed immediately"
            if not force:
                message += " (warning: current task may be lost)"

        else:
            return WorkerActionResponse(
                success=False,
                worker_id=worker_id,
                action=action,
                message=f"Unknown action: {action}",
            )

        return WorkerActionResponse(
            success=True,
            worker_id=worker_id,
            action=action,
            message=message,
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
        """Get logs from a worker.

        Args:
            worker_id: The worker to get logs from.
            level: Filter by log level.
            search: Search term to filter logs.
            limit: Maximum logs to return.
            offset: Pagination offset.

        Returns:
            WorkerLogsResponse with log entries, None if worker not found.
        """
        if worker_id not in self._workers:
            return None

        # Generate mock logs
        now = datetime.now(UTC)
        levels = ["INFO", "DEBUG", "INFO", "WARNING", "INFO", "ERROR", "INFO"]
        messages = [
            "Worker started successfully",
            "Connected to Redis broker at localhost:6379",
            "Registered for queues: default, high, emails",
            "Task send_email[abc123] received",
            "Task send_email[abc123] succeeded in 1.2s",
            "Connection to broker lost, reconnecting...",
            "Reconnected to broker",
            "Memory usage at 65%, considering cleanup",
            "Task process_payment[def456] failed: TimeoutError",
            "Retrying task process_payment[def456], attempt 2/3",
        ]

        logs = [
            WorkerLog(
                timestamp=now - timedelta(seconds=i * 30),
                level=levels[i % len(levels)],
                message=messages[i % len(messages)],
                logger_name="asynctasq.worker",
            )
            for i in range(50)
        ]

        # Apply filters
        if level is not None:
            logs = [log for log in logs if log.level == level.upper()]

        if search is not None:
            search_lower = search.lower()
            logs = [log for log in logs if search_lower in log.message.lower()]

        total = len(logs)
        logs = logs[offset : offset + limit]

        return WorkerLogsResponse(
            worker_id=worker_id,
            logs=logs,
            total=total,
            has_more=offset + len(logs) < total,
        )

    async def handle_heartbeat(self, request: HeartbeatRequest) -> HeartbeatResponse:
        """Process a heartbeat from a worker.

        Updates worker status and returns any pending commands.

        Args:
            request: The heartbeat request from the worker.

        Returns:
            HeartbeatResponse with any pending actions.
        """
        worker_id = request.worker_id
        now = datetime.now(UTC)

        # Update or create worker
        if worker_id in self._workers:
            worker = self._workers[worker_id]
            worker.status = request.status
            worker.current_task_id = request.current_task_id
            worker.current_task_name = request.current_task_name
            worker.last_heartbeat = now
            worker.cpu_usage = request.cpu_usage
            worker.memory_usage = request.memory_usage
            worker.memory_mb = request.memory_mb
            worker.tasks_processed = request.tasks_processed
            worker.tasks_failed = request.tasks_failed
            if worker.current_task_id is not None and worker.current_task_started_at is None:
                worker.current_task_started_at = now
            elif worker.current_task_id is None:
                worker.current_task_started_at = None
        else:
            # New worker registration
            worker = Worker(
                id=worker_id,
                name=worker_id,
                status=request.status,
                current_task_id=request.current_task_id,
                current_task_name=request.current_task_name,
                current_task_started_at=now if request.current_task_id else None,
                last_heartbeat=now,
                cpu_usage=request.cpu_usage,
                memory_usage=request.memory_usage,
                memory_mb=request.memory_mb,
                tasks_processed=request.tasks_processed,
                tasks_failed=request.tasks_failed,
                started_at=now,
            )
            self._workers[worker_id] = worker
            self._worker_logs[worker_id] = []
            self._pending_actions[worker_id] = {"pause": False, "shutdown": False}

        # Check for pending actions
        actions = self._pending_actions.get(worker_id, {})

        return HeartbeatResponse(
            received=True,
            timestamp=now,
            should_pause=actions.get("pause", False),
            should_shutdown=actions.get("shutdown", False),
        )

    async def mark_stale_workers_offline(
        self,
        timeout_seconds: int = 120,
    ) -> list[str]:
        """Mark workers as offline if no heartbeat received.

        Args:
            timeout_seconds: Seconds without heartbeat before marking offline.

        Returns:
            List of worker IDs that were marked offline.
        """
        marked_offline: list[str] = []

        for worker_id, worker in self._workers.items():
            if worker.status != WorkerStatus.OFFLINE:
                seconds_since = worker.seconds_since_heartbeat
                if seconds_since > timeout_seconds:
                    worker.status = WorkerStatus.OFFLINE
                    worker.current_task_id = None
                    worker.current_task_name = None
                    worker.current_task_started_at = None
                    marked_offline.append(worker_id)

        return marked_offline
