"""Tasks screen for browsing and managing tasks.

This module provides the TasksScreen which displays a filterable
list of tasks with the ability to view task details.
"""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Label

from asynctasq_monitor.models.task import Task, TaskFilters, TaskStatus
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
        """Load tasks when mounted."""
        # Set interval to refresh tasks periodically
        self.set_interval(2.0, self._refresh_tasks_from_backend)
        # Initial load
        self._refresh_tasks_from_backend()

    def _refresh_tasks_from_backend(self) -> None:
        """Fetch tasks from backend asynchronously."""
        # Start the worker to fetch tasks
        self._fetch_tasks_worker()

    @work(exclusive=False)
    async def _fetch_tasks_worker(self) -> None:
        """Fetch tasks and update the UI (worker method)."""
        try:
            from asynctasq_monitor.services.task_service import TaskService

            service = TaskService()
            filters = TaskFilters()
            tasks, _total = await service.get_tasks(filters, limit=100, offset=0)
            self.tasks = tasks
            self._update_table()
        except Exception:
            # If backend fetch fails, show empty state
            # Don't crash the TUI
            pass

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
