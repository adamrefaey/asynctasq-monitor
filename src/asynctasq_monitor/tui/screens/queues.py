"""Queues screen for monitoring queue depth, throughput, and management.

This module provides the QueuesScreen which displays all queues
with their health status, pending counts, and throughput metrics.
"""

from __future__ import annotations

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable, Label, Static

from asynctasq_monitor.models.queue import Queue, QueueStatus


class QueueTable(DataTable):
    """DataTable for displaying queues with health indicators and metrics.

    The table shows queue name, health status, pending count, throughput rate,
    workers assigned, and oldest task age. Rows are styled based on health.

    Events:
        QueueSelected: Emitted when a queue row is selected (Enter pressed).
    """

    HEALTH_COLORS: dict[str, str] = {
        "ok": "green",
        "warn": "yellow",
        "crit": "red",
        "paused": "cyan",
    }

    class QueueSelected(Message):
        """Emitted when a queue is selected by pressing Enter.

        Attributes:
            queue_name: The name of the selected queue.
        """

        def __init__(self, queue_name: str) -> None:
            """Initialize the message.

            Args:
                queue_name: The name of the selected queue.
            """
            super().__init__()
            self.queue_name = queue_name

    DEFAULT_CSS = """
    QueueTable {
        height: 1fr;
        margin: 0 1;
    }

    QueueTable > .datatable--cursor {
        background: $accent 30%;
    }
    """

    def on_mount(self) -> None:
        """Configure the table when mounted."""
        self.add_columns("Queue", "Health", "Pending", "Processing", "Rate", "Workers", "Oldest")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_queues(self, queues: list[Queue]) -> None:
        """Update the table with queue data.

        Clears existing rows and populates with new queue data.
        Health column is styled with appropriate colors based on depth.

        Args:
            queues: List of Queue objects to display.
        """
        self.clear()
        for queue in queues:
            health_status, health_color = self._get_health_status(queue)
            rate_display = self._format_rate(queue)
            oldest_display = self._format_oldest_task(queue)

            self.add_row(
                queue.name,
                Text(health_status, style=health_color),
                str(queue.depth),
                str(queue.processing),
                rate_display,
                str(queue.workers_assigned),
                oldest_display,
                key=queue.name,
            )

    def _get_health_status(self, queue: Queue) -> tuple[str, str]:
        """Determine health status based on queue state and depth.

        Args:
            queue: Queue object to evaluate.

        Returns:
            Tuple of (status_text, color_style).
        """
        if queue.status == QueueStatus.PAUSED:
            return ("⏸ Paused", self.HEALTH_COLORS["paused"])
        if queue.depth >= 500:
            return ("⊗ Crit", self.HEALTH_COLORS["crit"])
        if queue.depth >= 100:
            return ("⚠ Warn", self.HEALTH_COLORS["warn"])
        return ("● OK", self.HEALTH_COLORS["ok"])

    def _format_rate(self, queue: Queue) -> Text:
        """Format throughput rate with trend indicator.

        Args:
            queue: Queue object with throughput data.

        Returns:
            Rich Text object with styled rate display.
        """
        if queue.throughput_per_minute is None:
            return Text("─ 0/m", style="dim")

        rate = queue.throughput_per_minute
        # For now, show stable trend (─) since we don't have historical data
        # In the future, compare with previous rate to show ▲/▼
        return Text(f"─ {rate:.0f}/m", style="white")

    def _format_oldest_task(self, queue: Queue) -> str:
        """Format the age of the oldest task in the queue.

        Args:
            queue: Queue object (oldest_task_age_seconds would be an attribute).

        Returns:
            Human-readable relative time string.
        """
        # For sample data, we'll use a placeholder
        # In production, this would come from queue.oldest_task_age_seconds
        if queue.depth == 0:
            return "-"
        # Placeholder for demo - would come from actual data
        return "~1m"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection and emit QueueSelected message.

        Args:
            event: The row selection event.
        """
        if event.row_key is not None:
            self.post_message(self.QueueSelected(str(event.row_key.value)))


class QueueSummary(Horizontal):
    """Summary bar showing overall queue statistics.

    Displays total queues, total pending tasks, and aggregate throughput.
    """

    total_queues: reactive[int] = reactive(0)
    total_pending: reactive[int] = reactive(0)
    total_rate: reactive[float] = reactive(0.0)

    DEFAULT_CSS = """
    QueueSummary {
        height: 3;
        margin: 0 1 1 1;
        padding: 0 1;
        background: $panel;
        border: solid $primary-darken-2;
    }

    QueueSummary Static {
        width: 1fr;
        text-align: center;
        content-align: center middle;
    }

    QueueSummary .summary-queues {
        color: $primary;
    }

    QueueSummary .summary-pending {
        color: $warning;
    }

    QueueSummary .summary-rate {
        color: $success;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the summary UI."""
        yield Static("📬 Queues: 0", id="queue-count", classes="summary-queues")
        yield Static("⏳ Pending: 0", id="pending-count", classes="summary-pending")
        yield Static("⚡ Rate: 0/m", id="rate-display", classes="summary-rate")

    def watch_total_queues(self, count: int) -> None:
        """Update queue count display.

        Args:
            count: New queue count.
        """
        self.query_one("#queue-count", Static).update(f"📬 Queues: {count}")

    def watch_total_pending(self, count: int) -> None:
        """Update pending count display.

        Args:
            count: New total pending count.
        """
        self.query_one("#pending-count", Static).update(f"⏳ Pending: {count:,}")

    def watch_total_rate(self, rate: float) -> None:
        """Update total rate display.

        Args:
            rate: New aggregate throughput rate.
        """
        self.query_one("#rate-display", Static).update(f"⚡ Rate: {rate:.0f}/m")

    def update_stats(self, queues: list[Queue]) -> None:
        """Update all statistics from queue list.

        Args:
            queues: List of Queue objects to aggregate.
        """
        self.total_queues = len(queues)
        self.total_pending = sum(q.depth for q in queues)
        self.total_rate = sum(q.throughput_per_minute or 0.0 for q in queues)


class QueuesScreen(Container):
    """Queue monitoring screen.

    Displays a summary of queue statistics and a detailed table
    of all queues with their health status and metrics.

    Key Features:
        - Health indicators based on queue depth thresholds
        - Throughput rate display with trend indicators
        - Worker assignment counts
        - Oldest task age for queue backlog visibility
    """

    # Reactive queue list
    queues: reactive[list[Queue]] = reactive(list, recompose=False)

    DEFAULT_CSS = """
    QueuesScreen {
        height: 100%;
        padding: 1;
    }

    QueuesScreen .section-title {
        margin: 0 0 0 1;
        text-style: bold;
        color: $text;
    }

    QueuesScreen #queue-table {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the queues screen UI."""
        yield Label("📬 Queues", classes="section-title")
        yield QueueSummary(id="queue-summary")
        yield QueueTable(id="queue-table")

    def on_mount(self) -> None:
        """Load sample data when mounted."""
        self._load_sample_data()

    def _load_sample_data(self) -> None:
        """Load sample queue data for development/testing."""
        sample_queues = [
            Queue(
                name="default",
                status=QueueStatus.ACTIVE,
                depth=42,
                processing=3,
                completed_total=15678,
                failed_total=23,
                workers_assigned=3,
                throughput_per_minute=45.2,
                avg_duration_ms=234.5,
            ),
            Queue(
                name="high",
                status=QueueStatus.ACTIVE,
                depth=8,
                processing=2,
                completed_total=8923,
                failed_total=12,
                workers_assigned=2,
                throughput_per_minute=28.5,
                avg_duration_ms=156.2,
            ),
            Queue(
                name="email",
                status=QueueStatus.PAUSED,
                depth=0,
                processing=0,
                completed_total=45678,
                failed_total=89,
                workers_assigned=0,
                throughput_per_minute=0.0,
                avg_duration_ms=1234.5,
            ),
            Queue(
                name="report",
                status=QueueStatus.ACTIVE,
                depth=156,
                processing=1,
                completed_total=2345,
                failed_total=56,
                workers_assigned=1,
                throughput_per_minute=8.2,
                avg_duration_ms=5678.9,
            ),
            Queue(
                name="low",
                status=QueueStatus.ACTIVE,
                depth=12,
                processing=1,
                completed_total=3456,
                failed_total=7,
                workers_assigned=1,
                throughput_per_minute=12.3,
                avg_duration_ms=345.6,
            ),
        ]

        self.queues = sample_queues
        self._update_display()

    def _update_display(self) -> None:
        """Update all display components with current queue data."""
        # Update table
        table = self.query_one(QueueTable)
        table.update_queues(self.queues)

        # Update summary
        summary = self.query_one(QueueSummary)
        summary.update_stats(self.queues)

    def update_queues(self, queues: list[Queue]) -> None:
        """Update the screen with new queue data.

        Args:
            queues: List of Queue objects to display.
        """
        self.queues = queues
        self._update_display()

    @on(QueueTable.QueueSelected)
    def handle_queue_selected(self, event: QueueTable.QueueSelected) -> None:
        """Handle queue selection - show notification for now.

        In the future, this will open a queue detail modal.

        Args:
            event: The queue selected event.
        """
        self.notify(f"Selected queue: {event.queue_name}")
        # TODO: Open queue detail modal
        # from asynctasq_monitor.tui.screens.queue_detail import QueueDetailScreen
        # self.app.push_screen(QueueDetailScreen(event.queue_name))
