"""Task table widget for displaying task list.

This module provides the TaskTable widget which displays tasks in a
DataTable with status colors, row selection, and keyboard navigation.

Design Principles (2024-2025 Best Practices):
- Semantic status colors for clear visual feedback
- Status icons for quick recognition
- Zebra striping for readability
"""

import logging

from rich.text import Text
from textual.message import Message
from textual.widgets import DataTable

from asynctasq_monitor.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskTable(DataTable):
    """DataTable for displaying tasks with status colors and icons.

    The table shows task ID, name, queue, status, worker, and duration.
    Rows are styled with colors based on task status, with icons for
    quick visual recognition.

    Events:
        TaskSelected: Emitted when a task row is selected (Enter pressed).

    Example:
        >>> table = TaskTable(id="task-table")
        >>> table.update_tasks(tasks)  # Update with list of Task objects
    """

    # Status colors and icons for visual feedback
    STATUS_STYLES: dict[str, tuple[str, str]] = {
        "pending": ("yellow", ""),
        "running": ("cyan", ""),
        "completed": ("green", ""),
        "failed": ("red", ""),
        "retrying": ("orange1", ""),
        "cancelled": ("dim", ""),
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
        Status column is styled with appropriate colors and icons.
        Completed and cancelled tasks are shown with dimmed styling.

        Args:
            tasks: List of Task objects to display.
        """
        logger.info("TaskTable.update_tasks called with %d tasks", len(tasks))
        self.clear()

        # Sort tasks: incomplete first (by status priority), then by enqueued time
        status_priority = {
            TaskStatus.RUNNING: 0,
            TaskStatus.RETRYING: 1,
            TaskStatus.PENDING: 2,
            TaskStatus.FAILED: 3,
            TaskStatus.COMPLETED: 4,
            TaskStatus.CANCELLED: 5,
        }

        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                status_priority.get(t.status, 99),
                t.enqueued_at,
            ),
        )

        for task in sorted_tasks:
            status_value = task.status.value if isinstance(task.status, TaskStatus) else task.status
            color, icon = self.STATUS_STYLES.get(status_value, ("white", ""))

            # Apply dim styling for completed/cancelled tasks
            is_done = task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
            base_style = "dim" if is_done else ""

            # Format worker ID (truncate if present)
            worker_display = task.worker_id[:8] if task.worker_id else "-"

            # Format duration with appropriate unit
            if task.duration_ms is not None:
                if task.duration_ms >= 1000:
                    duration_display = f"{task.duration_ms / 1000:.1f}s"
                else:
                    duration_display = f"{task.duration_ms}ms"
            else:
                duration_display = "-"

            # Status with icon
            status_display = f"{icon} {status_value}"

            self.add_row(
                Text(task.id[:8], style=base_style or "dim"),
                Text(task.name, style=base_style),
                Text(task.queue, style=f"{base_style} italic" if base_style else "italic"),
                Text(status_display, style=f"{color} bold" if not is_done else f"{color}"),
                Text(worker_display, style=base_style or "dim"),
                Text(duration_display, style=base_style),
                key=task.id,
            )
            logger.debug("Added row for task %s: %s", task.id[:8], task.name)

        logger.info("TaskTable now has %d rows", self.row_count)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - emit custom TaskSelected message.

        Args:
            event: The row selection event from DataTable.
        """
        event.stop()
        if event.row_key is not None:
            self.post_message(self.TaskSelected(str(event.row_key.value)))
