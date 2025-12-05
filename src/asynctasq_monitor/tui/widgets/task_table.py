"""Task table widget for displaying task list.

This module provides the TaskTable widget which displays tasks in a
DataTable with status colors, row selection, and keyboard navigation.
"""

from __future__ import annotations

from rich.text import Text
from textual.message import Message
from textual.widgets import DataTable

from asynctasq_monitor.models.task import Task, TaskStatus


class TaskTable(DataTable):
    """DataTable for displaying tasks with status colors.

    The table shows task ID, name, queue, status, worker, and duration.
    Rows are styled with colors based on task status.

    Events:
        TaskSelected: Emitted when a task row is selected (Enter pressed).

    Example:
        >>> table = TaskTable(id="task-table")
        >>> table.update_tasks(tasks)  # Update with list of Task objects
    """

    STATUS_COLORS: dict[str, str] = {
        "pending": "yellow",
        "running": "cyan",
        "completed": "green",
        "failed": "red",
        "retrying": "orange1",
        "cancelled": "dim",
    }

    class TaskSelected(Message):
        """Emitted when a task is selected by pressing Enter.

        Attributes:
            task_id: The ID of the selected task.
        """

        def __init__(self, task_id: str) -> None:
            """Initialize the message.

            Args:
                task_id: The ID of the selected task.
            """
            super().__init__()
            self.task_id = task_id

    DEFAULT_CSS = """
    TaskTable {
        height: 1fr;
        margin: 0 1;
    }

    TaskTable > .datatable--cursor {
        background: $accent 30%;
    }
    """

    def on_mount(self) -> None:
        """Configure the table when mounted."""
        self.add_columns("ID", "Name", "Queue", "Status", "Worker", "Duration")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_tasks(self, tasks: list[Task]) -> None:
        """Update the table with task data.

        Clears existing rows and populates with new task data.
        Status column is styled with appropriate colors.

        Args:
            tasks: List of Task objects to display.
        """
        self.clear()
        for task in tasks:
            status_value = task.status.value if isinstance(task.status, TaskStatus) else task.status
            color = self.STATUS_COLORS.get(status_value, "white")

            # Format worker ID (truncate if present)
            worker_display = task.worker_id[:8] if task.worker_id else "-"

            # Format duration
            duration_display = f"{task.duration_ms}ms" if task.duration_ms is not None else "-"

            self.add_row(
                task.id[:8],
                task.name,
                task.queue,
                Text(status_value, style=color),
                worker_display,
                duration_display,
                key=task.id,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - emit custom TaskSelected message.

        Args:
            event: The row selection event from DataTable.
        """
        event.stop()
        if event.row_key is not None:
            self.post_message(self.TaskSelected(str(event.row_key.value)))
