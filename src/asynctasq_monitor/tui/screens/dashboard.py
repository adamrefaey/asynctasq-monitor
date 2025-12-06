"""Dashboard screen with metrics overview.

This module provides the DashboardScreen which displays an overview
of task queue metrics, throughput charts, and recent activity.

Design Principles (2024-2025 Best Practices):
- Clear visual hierarchy with semantic colors
- Responsive layout using fractional units
- Real-time updates via reactive attributes
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Label, Sparkline, Static

from asynctasq_monitor.tui.widgets.metric_card import MetricCard


class DashboardScreen(Container):
    """Main dashboard with metrics overview.

    Displays four metric cards (pending, running, completed, failed),
    a throughput sparkline chart, and recent activity list.
    """

    # Reactive metric counters
    pending_count: reactive[int] = reactive(0)
    running_count: reactive[int] = reactive(0)
    completed_count: reactive[int] = reactive(0)
    failed_count: reactive[int] = reactive(0)

    # Throughput data for sparkline
    throughput_data: reactive[list[float]] = reactive(list, recompose=False)

    def compose(self) -> ComposeResult:
        """Compose the dashboard UI."""
        with Horizontal(id="metrics-row"):
            yield MetricCard("Pending", "pending", variant="warning", icon="")
            yield MetricCard("Running", "running", variant="accent", icon="")
            yield MetricCard("Completed", "completed", variant="success", icon="")
            yield MetricCard("Failed", "failed", variant="error", icon="")

        with Container(id="throughput-container"):
            yield Label("Throughput (tasks/min)", classes="container-title")
            yield Sparkline([], id="throughput-sparkline")

        with VerticalScroll(id="recent-activity"):
            yield Label("Recent Activity", classes="container-title")
            yield Static("Waiting for events...", id="activity-log", classes="activity-log")

    def watch_pending_count(self, value: int) -> None:
        """Update pending metric card when count changes."""
        try:
            self.query_one("#pending", MetricCard).value = value
        except Exception:
            pass

    def watch_running_count(self, value: int) -> None:
        """Update running metric card when count changes."""
        try:
            self.query_one("#running", MetricCard).value = value
        except Exception:
            pass

    def watch_completed_count(self, value: int) -> None:
        """Update completed metric card when count changes."""
        try:
            self.query_one("#completed", MetricCard).value = value
        except Exception:
            pass

    def watch_failed_count(self, value: int) -> None:
        """Update failed metric card when count changes."""
        try:
            self.query_one("#failed", MetricCard).value = value
        except Exception:
            pass

    def watch_throughput_data(self, data: list[float]) -> None:
        """Update sparkline when throughput data changes."""
        try:
            sparkline = self.query_one("#throughput-sparkline", Sparkline)
            sparkline.data = data
        except Exception:
            pass

    def update_metrics(
        self,
        pending: int,
        running: int,
        completed: int,
        failed: int,
    ) -> None:
        """Update all metric values at once.

        Args:
            pending: Number of pending tasks.
            running: Number of running tasks.
            completed: Number of completed tasks.
            failed: Number of failed tasks.
        """
        self.pending_count = pending
        self.running_count = running
        self.completed_count = completed
        self.failed_count = failed

    def add_throughput_sample(self, tasks_per_minute: float) -> None:
        """Add a new throughput sample to the sparkline.

        Keeps the last 60 samples (approximately 1 hour at 1 sample/min).

        Args:
            tasks_per_minute: Current throughput rate.
        """
        # Create a new list to trigger reactivity
        current_data = list(self.throughput_data)
        current_data.append(tasks_per_minute)
        # Keep last 60 samples
        if len(current_data) > 60:
            current_data = current_data[-60:]
        self.throughput_data = current_data

    def update_activity(self, activity_text: str) -> None:
        """Update the recent activity display.

        Args:
            activity_text: Text to display in the activity section.
        """
        try:
            activity = self.query_one("#activity-log", Static)
            activity.update(activity_text)
        except Exception:
            pass
