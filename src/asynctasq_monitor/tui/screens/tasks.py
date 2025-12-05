"""Tasks screen for browsing and managing tasks.

This module provides the TasksScreen which displays a filterable
list of tasks with the ability to view task details.
"""

from __future__ import annotations

from datetime import UTC, datetime

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Label

from asynctasq_monitor.models.task import Task, TaskStatus
from asynctasq_monitor.tui.widgets.filter_bar import FilterBar
from asynctasq_monitor.tui.widgets.task_table import TaskTable


class TasksScreen(Container):
    """Task list screen with filters and actions.

    Displays a searchable, filterable table of tasks. Selecting a task
    opens a detail modal. Supports keyboard navigation (j/k for up/down,
    Enter to open details).
    """

    STATUSES: list[str] = [
        "pending",
        "running",
        "completed",
        "failed",
        "retrying",
        "cancelled",
    ]
    QUEUES: list[str] = ["default", "high", "low", "email", "report"]

    # Reactive task list
    tasks: reactive[list[Task]] = reactive(list, recompose=False)

    # Current filter state
    _current_search: str = ""
    _current_status: str = "All Status"
    _current_queue: str = "All Queues"

    DEFAULT_CSS = """
    TasksScreen {
        height: 100%;
        padding: 1;
    }

    TasksScreen > .section-title {
        margin: 0 0 1 1;
        text-style: bold;
        color: $text;
    }

    TasksScreen > #no-tasks-label {
        width: 100%;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the tasks screen UI."""
        yield Label("📋 Tasks", classes="section-title")
        yield FilterBar(
            statuses=self.STATUSES,
            queues=self.QUEUES,
            id="filter-bar",
        )
        yield TaskTable(id="task-table")

    def on_mount(self) -> None:
        """Load sample data when mounted."""
        self._load_sample_data()

    def _load_sample_data(self) -> None:
        """Load sample task data for development/demo."""
        now = datetime.now(UTC)

        sample_tasks = [
            Task(
                id="abc12345-1234-5678-9abc-def012345678",
                name="send_email",
                queue="email",
                status=TaskStatus.COMPLETED,
                enqueued_at=now,
                started_at=now,
                completed_at=now,
                duration_ms=234,
            ),
            Task(
                id="def45678-1234-5678-9abc-def012345678",
                name="process_payment",
                queue="high",
                status=TaskStatus.RUNNING,
                enqueued_at=now,
                started_at=now,
                worker_id="worker-1234-abcd",
            ),
            Task(
                id="ghi78901-1234-5678-9abc-def012345678",
                name="generate_report",
                queue="report",
                status=TaskStatus.FAILED,
                enqueued_at=now,
                started_at=now,
                completed_at=now,
                duration_ms=5000,
                exception="ReportGenerationError: Failed to fetch data",
            ),
            Task(
                id="jkl01234-1234-5678-9abc-def012345678",
                name="sync_inventory",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
            Task(
                id="mno56789-1234-5678-9abc-def012345678",
                name="send_notification",
                queue="low",
                status=TaskStatus.RETRYING,
                enqueued_at=now,
                started_at=now,
                worker_id="worker-5678-efgh",
                attempt=2,
                max_retries=3,
            ),
            Task(
                id="pqr23456-1234-5678-9abc-def012345678",
                name="cleanup_temp_files",
                queue="default",
                status=TaskStatus.CANCELLED,
                enqueued_at=now,
            ),
        ]

        self.tasks = sample_tasks
        self._update_table()

    def _update_table(self) -> None:
        """Update the task table with filtered tasks."""
        filtered_tasks = self._filter_tasks(self.tasks)
        table = self.query_one("#task-table", TaskTable)
        table.update_tasks(filtered_tasks)

    def _filter_tasks(self, tasks: list[Task]) -> list[Task]:
        """Apply current filters to task list.

        Args:
            tasks: List of tasks to filter.

        Returns:
            Filtered list of tasks.
        """
        result = tasks

        # Filter by search term
        if self._current_search:
            search_lower = self._current_search.lower()
            result = [
                t for t in result if search_lower in t.name.lower() or search_lower in t.id.lower()
            ]

        # Filter by status
        if self._current_status != "All Status":
            result = [
                t
                for t in result
                if (t.status.value if isinstance(t.status, TaskStatus) else t.status)
                == self._current_status
            ]

        # Filter by queue
        if self._current_queue != "All Queues":
            result = [t for t in result if t.queue == self._current_queue]

        return result

    @on(FilterBar.FilterChanged)
    def _handle_filter_change(self, event: FilterBar.FilterChanged) -> None:
        """Handle filter changes from the FilterBar.

        Args:
            event: The filter changed event.
        """
        self._current_search = event.search
        self._current_status = event.status
        self._current_queue = event.queue
        self._update_table()

    @on(TaskTable.TaskSelected)
    def _handle_task_selected(self, event: TaskTable.TaskSelected) -> None:
        """Open task detail modal when a task is selected.

        Args:
            event: The task selected event.
        """
        from asynctasq_monitor.tui.screens.task_detail import TaskDetailScreen

        # Find the full task data
        task = next((t for t in self.tasks if t.id == event.task_id), None)
        if task:
            self.app.push_screen(TaskDetailScreen(task))

    def refresh_tasks(self, tasks: list[Task]) -> None:
        """Refresh the task list with new data.

        Args:
            tasks: New list of tasks to display.
        """
        self.tasks = tasks
        self._update_table()
