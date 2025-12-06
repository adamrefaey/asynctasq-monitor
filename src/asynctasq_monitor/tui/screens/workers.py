"""Workers screen for displaying worker list and status.

This module provides the WorkersScreen which shows all workers
with their status, resource usage, and current tasks.
"""

import logging

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable, Label, Static

from asynctasq_monitor.models.worker import Worker, WorkerStatus

logger = logging.getLogger(__name__)


class WorkerTable(DataTable):
    """DataTable for displaying workers with status colors and resource usage.

    The table shows worker ID, status, queue(s), current task, CPU, memory,
    and heartbeat. Rows are styled with colors based on worker status.

    Events:
        WorkerSelected: Emitted when a worker row is selected (Enter pressed).
    """

    STATUS_COLORS: dict[str, str] = {
        "active": "green",
        "idle": "yellow",
        "offline": "red",
    }

    class WorkerSelected(Message):
        """Emitted when a worker is selected by pressing Enter.

        Attributes:
            worker_id: The ID of the selected worker.
        """

        def __init__(self, worker_id: str) -> None:
            """Initialize the message.

            Args:
                worker_id: The ID of the selected worker.
            """
            super().__init__()
            self.worker_id = worker_id

    DEFAULT_CSS = """
    WorkerTable {
        height: 1fr;
        margin: 0 1;
    }

    WorkerTable > .datatable--cursor {
        background: $accent 30%;
    }
    """

    def on_mount(self) -> None:
        """Configure the table when mounted."""
        self.add_columns("ID", "Status", "Queue(s)", "Current Task", "CPU", "Memory", "Heartbeat")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_workers(self, workers: list[Worker]) -> None:
        """Update the table with worker data.

        Clears existing rows and populates with new worker data.
        Status column is styled with appropriate colors.

        Args:
            workers: List of Worker objects to display.
        """
        self.clear()
        for worker in workers:
            status_value = (
                worker.status.value if isinstance(worker.status, WorkerStatus) else worker.status
            )
            color = self.STATUS_COLORS.get(status_value, "white")

            # Format queues (join with comma, truncate if too long)
            queues_display = ", ".join(worker.queues[:3])
            if len(worker.queues) > 3:
                queues_display += f" (+{len(worker.queues) - 3})"

            # Format current task
            task_display = worker.current_task_name if worker.current_task_name else "-"

            # Format CPU usage
            cpu_display = f"{worker.cpu_usage:.0f}%" if worker.cpu_usage is not None else "-"

            # Format memory usage
            if worker.memory_mb is not None:
                memory_display = f"{worker.memory_mb}MB"
            elif worker.memory_usage is not None:
                memory_display = f"{worker.memory_usage:.0f}%"
            else:
                memory_display = "-"

            # Format heartbeat (relative time)
            heartbeat_display = self._format_heartbeat(worker)

            self.add_row(
                worker.id[:12],
                Text(status_value.capitalize(), style=color),
                queues_display,
                task_display,
                cpu_display,
                memory_display,
                heartbeat_display,
                key=worker.id,
            )

    def _format_heartbeat(self, worker: Worker) -> str:
        """Format heartbeat timestamp as relative time.

        Args:
            worker: Worker object with last_heartbeat.

        Returns:
            Human-readable relative time string.
        """
        from datetime import UTC, datetime

        if worker.last_heartbeat is None:
            return "-"

        now = datetime.now(UTC)
        # Ensure both datetimes are offset-aware for comparison
        last_hb = worker.last_heartbeat
        if last_hb.tzinfo is None:
            # Assume UTC if naive
            from datetime import UTC

            last_hb = last_hb.replace(tzinfo=UTC)

        diff = now - last_hb
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        else:
            days = seconds // 86400
            return f"{days}d ago"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection and emit WorkerSelected message.

        Args:
            event: The row selection event.
        """
        if event.row_key is not None:
            self.post_message(self.WorkerSelected(str(event.row_key.value)))


class WorkerSummary(Horizontal):
    """Summary bar showing worker status counts.

    Displays counts of active, idle, and offline workers with
    color-coded indicators.
    """

    # Reactive counts that trigger UI updates
    active_count: reactive[int] = reactive(0)
    idle_count: reactive[int] = reactive(0)
    offline_count: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    WorkerSummary {
        height: 3;
        margin: 0 1 1 1;
        padding: 0 1;
        background: $panel;
        border: solid $primary-darken-2;
    }

    WorkerSummary Static {
        width: 1fr;
        text-align: center;
        content-align: center middle;
    }

    WorkerSummary .summary-active {
        color: $success;
    }

    WorkerSummary .summary-idle {
        color: $warning;
    }

    WorkerSummary .summary-offline {
        color: $error;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the summary UI."""
        yield Static("🟢 Active: 0", id="active-count", classes="summary-active")
        yield Static("🟡 Idle: 0", id="idle-count", classes="summary-idle")
        yield Static("🔴 Offline: 0", id="offline-count", classes="summary-offline")

    def watch_active_count(self, count: int) -> None:
        """Update active count display.

        Args:
            count: New active worker count.
        """
        self.query_one("#active-count", Static).update(f"🟢 Active: {count}")

    def watch_idle_count(self, count: int) -> None:
        """Update idle count display.

        Args:
            count: New idle worker count.
        """
        self.query_one("#idle-count", Static).update(f"🟡 Idle: {count}")

    def watch_offline_count(self, count: int) -> None:
        """Update offline count display.

        Args:
            count: New offline worker count.
        """
        self.query_one("#offline-count", Static).update(f"🔴 Offline: {count}")

    def update_counts(self, active: int, idle: int, offline: int) -> None:
        """Update all counts at once.

        Args:
            active: Number of active workers.
            idle: Number of idle workers.
            offline: Number of offline workers.
        """
        self.active_count = active
        self.idle_count = idle
        self.offline_count = offline


class WorkersScreen(Container):
    """Worker monitoring screen.

    Displays a summary of worker statuses and a detailed table
    of all workers with their current state and resource usage.
    """

    DEFAULT_CSS = """
    WorkersScreen {
        height: 100%;
        padding: 1;
    }

    WorkersScreen .section-title {
        margin: 0 0 0 1;
        text-style: bold;
        color: $text;
    }

    WorkersScreen #worker-table {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the workers screen UI."""
        yield Label("👷 Workers", classes="section-title")
        yield WorkerSummary(id="worker-summary")
        yield WorkerTable(id="worker-table")

    def on_mount(self) -> None:
        """Load worker data when mounted."""
        # Set interval to refresh workers periodically
        self.set_interval(2.0, self._refresh_workers_from_backend)
        # Initial load
        self._refresh_workers_from_backend()

    def _refresh_workers_from_backend(self) -> None:
        """Fetch workers from backend asynchronously."""
        self._fetch_workers_worker()

    @work(exclusive=False)
    async def _fetch_workers_worker(self) -> None:
        """Fetch workers and update the UI (worker method)."""
        try:
            from asynctasq_monitor.services.worker_service import WorkerService

            service = WorkerService()
            response = await service.get_workers()
            logger.info("Fetched %d workers from backend", response.total)
            self._update_worker_display(response.items)
        except Exception as e:
            logger.exception("Failed to fetch workers from backend: %s", e)
            # Don't crash the TUI

    def _update_worker_display(self, workers: list[Worker]) -> None:
        """Update the display with worker data."""
        try:
            # Update table
            table = self.query_one(WorkerTable)
            table.update_workers(workers)

            # Update summary counts
            summary = self.query_one(WorkerSummary)
            active_count = sum(1 for w in workers if w.status == WorkerStatus.ACTIVE)
            idle_count = sum(1 for w in workers if w.status == WorkerStatus.IDLE)
            offline_count = sum(1 for w in workers if w.status == WorkerStatus.OFFLINE)
            summary.update_counts(active_count, idle_count, offline_count)
        except Exception:
            pass  # Display not mounted yet

    def update_workers(self, workers: list[Worker]) -> None:
        """Update the screen with new worker data.

        Args:
            workers: List of Worker objects to display.
        """
        # Update table
        table = self.query_one(WorkerTable)
        table.update_workers(workers)

        # Update summary counts
        summary = self.query_one(WorkerSummary)
        active_count = sum(1 for w in workers if w.status == WorkerStatus.ACTIVE)
        idle_count = sum(1 for w in workers if w.status == WorkerStatus.IDLE)
        offline_count = sum(1 for w in workers if w.status == WorkerStatus.OFFLINE)
        summary.update_counts(active_count, idle_count, offline_count)

    @on(WorkerTable.WorkerSelected)
    def handle_worker_selected(self, event: WorkerTable.WorkerSelected) -> None:
        """Handle worker selection - show notification for now.

        In the future, this will open a worker detail modal.

        Args:
            event: The worker selected event.
        """
        self.notify(f"Selected worker: {event.worker_id}")
        # TODO: Open worker detail modal
        # from asynctasq_monitor.tui.screens.worker_detail import WorkerDetailScreen
        # self.app.push_screen(WorkerDetailScreen(event.worker_id))
