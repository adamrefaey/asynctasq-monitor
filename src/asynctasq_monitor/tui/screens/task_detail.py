"""Task detail modal screen.

This module provides the TaskDetailScreen which displays detailed
information about a single task with action buttons.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from asynctasq_monitor.models.task import Task, TaskStatus


class TaskDetailScreen(ModalScreen[bool]):
    """Modal screen showing detailed task information.

    Displays task metadata, timeline, arguments, and result/exception.
    Provides action buttons for retry, cancel, and close operations.

    Returns:
        True if an action was taken (retry/cancel), False otherwise.
    """

    BINDINGS = [("escape", "close_modal", "Close")]

    DEFAULT_CSS = """
    TaskDetailScreen {
        align: center middle;
    }

    #task-detail-container {
        width: 80%;
        max-width: 100;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #task-detail-header {
        height: 3;
        margin-bottom: 1;
    }

    #task-detail-header Label {
        text-style: bold;
        color: $primary;
    }

    #task-detail-content {
        height: auto;
        max-height: 50;
        margin-bottom: 1;
        overflow-y: auto;
    }

    .detail-section {
        margin-bottom: 1;
    }

    .detail-section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
    }

    .detail-row {
        height: auto;
    }

    .detail-label {
        width: 18;
        color: $text-muted;
    }

    .detail-value {
        width: 1fr;
    }

    .status-pending {
        color: $warning;
    }

    .status-running {
        color: $accent;
    }

    .status-completed {
        color: $success;
    }

    .status-failed {
        color: $error;
    }

    .status-retrying {
        color: $warning;
    }

    .status-cancelled {
        color: $text-muted;
    }

    #exception-content {
        background: $error 10%;
        border: solid $error;
        padding: 1;
        color: $error;
        max-height: 10;
        overflow-y: auto;
    }

    #result-content {
        background: $success 10%;
        border: solid $success;
        padding: 1;
        max-height: 10;
        overflow-y: auto;
    }

    #args-content {
        background: $panel;
        border: solid $primary-darken-2;
        padding: 1;
        max-height: 6;
        overflow-y: auto;
    }

    #task-detail-actions {
        height: 3;
        align: right middle;
    }

    #task-detail-actions Button {
        margin-left: 1;
    }
    """

    def __init__(self, task_data: Task) -> None:
        """Initialize the task detail screen.

        Args:
            task_data: The task to display.
        """
        super().__init__()
        self._task_data = task_data

    @property
    def task_data(self) -> Task:
        """Get the task being displayed."""
        return self._task_data

    def compose(self) -> ComposeResult:
        """Compose the task detail UI."""
        with Container(id="task-detail-container"):
            with Horizontal(id="task-detail-header"):
                yield Label(f"📋 Task: {self._task_data.id[:16]}...")

            with Vertical(id="task-detail-content"):
                # Basic Info Section
                yield Label("Identity", classes="detail-section-title")
                with Container(classes="detail-section"):
                    yield from self._detail_row("ID:", self._task_data.id)
                    yield from self._detail_row("Name:", self._task_data.name)
                    yield from self._detail_row("Queue:", self._task_data.queue)
                    yield from self._status_row()

                # Timeline Section
                yield Label("Timeline", classes="detail-section-title")
                with Container(classes="detail-section"):
                    yield from self._detail_row(
                        "Enqueued:",
                        self._format_datetime(self._task_data.enqueued_at),
                    )
                    yield from self._detail_row(
                        "Started:",
                        self._format_datetime(self._task_data.started_at),
                    )
                    yield from self._detail_row(
                        "Completed:",
                        self._format_datetime(self._task_data.completed_at),
                    )
                    yield from self._detail_row(
                        "Duration:",
                        f"{self._task_data.duration_ms}ms" if self._task_data.duration_ms else "-",
                    )

                # Execution Section
                yield Label("Execution", classes="detail-section-title")
                with Container(classes="detail-section"):
                    yield from self._detail_row(
                        "Worker:",
                        self._task_data.worker_id or "-",
                    )
                    yield from self._detail_row(
                        "Attempt:",
                        f"{self._task_data.attempt}/{self._task_data.max_retries}",
                    )
                    yield from self._detail_row(
                        "Priority:",
                        str(self._task_data.priority),
                    )
                    yield from self._detail_row(
                        "Timeout:",
                        f"{self._task_data.timeout_seconds}s"
                        if self._task_data.timeout_seconds
                        else "-",
                    )

                # Arguments Section (if present)
                if self._task_data.args or self._task_data.kwargs:
                    yield Label("Arguments", classes="detail-section-title")
                    args_text = self._format_args()
                    yield Static(args_text, id="args-content")

                # Result Section (if completed)
                if self._task_data.result is not None:
                    yield Label("Result", classes="detail-section-title")
                    yield Static(str(self._task_data.result), id="result-content")

                # Exception Section (if failed)
                if self._task_data.exception:
                    yield Label("Exception", classes="detail-section-title")
                    exception_text: str = self._task_data.exception
                    if self._task_data.traceback:
                        exception_text = f"{exception_text}\n\n{self._task_data.traceback}"
                    yield Static(exception_text, id="exception-content")

            with Horizontal(id="task-detail-actions"):
                # Only show retry for failed/cancelled tasks
                if self._can_retry():
                    yield Button("Retry", id="retry-btn", variant="primary")
                # Only show cancel for pending/running tasks
                if self._can_cancel():
                    yield Button("Cancel", id="cancel-btn", variant="warning")
                yield Button("Close", id="close-btn")

    def _detail_row(self, label: str, value: str) -> ComposeResult:
        """Create a detail row with label and value.

        Args:
            label: The label text.
            value: The value text.

        Yields:
            A Horizontal container with label and value.
        """
        with Horizontal(classes="detail-row"):
            yield Label(label, classes="detail-label")
            yield Label(value, classes="detail-value")

    def _status_row(self) -> ComposeResult:
        """Create a status row with colored status value.

        Yields:
            A Horizontal container with status label and colored value.
        """
        status_value = (
            self._task_data.status.value
            if isinstance(self._task_data.status, TaskStatus)
            else str(self._task_data.status)
        )
        with Horizontal(classes="detail-row"):
            yield Label("Status:", classes="detail-label")
            yield Label(status_value, classes=f"detail-value status-{status_value}")

    def _format_datetime(self, dt: object) -> str:
        """Format a datetime for display.

        Args:
            dt: Datetime to format (or None).

        Returns:
            Formatted datetime string or "-" if None.
        """
        if dt is None:
            return "-"
        if hasattr(dt, "strftime"):
            return dt.strftime("%Y-%m-%d %H:%M:%S")  # type: ignore[union-attr]
        return str(dt)

    def _format_args(self) -> str:
        """Format task arguments for display.

        Returns:
            Formatted arguments string.
        """
        lines: list[str] = []
        if self._task_data.args:
            lines.append(f"args: {self._task_data.args}")
        if self._task_data.kwargs:
            lines.append(f"kwargs: {self._task_data.kwargs}")
        return "\n".join(lines) if lines else "-"

    def _can_retry(self) -> bool:
        """Check if the task can be retried.

        Returns:
            True if task can be retried.
        """
        status = (
            self._task_data.status
            if isinstance(self._task_data.status, TaskStatus)
            else TaskStatus(str(self._task_data.status))
        )
        return status in {TaskStatus.FAILED, TaskStatus.CANCELLED}

    def _can_cancel(self) -> bool:
        """Check if the task can be cancelled.

        Returns:
            True if task can be cancelled.
        """
        status = (
            self._task_data.status
            if isinstance(self._task_data.status, TaskStatus)
            else TaskStatus(str(self._task_data.status))
        )
        return status in {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING}

    @on(Button.Pressed, "#close-btn")
    def _handle_close(self) -> None:
        """Handle close button press."""
        self.dismiss(False)

    @on(Button.Pressed, "#retry-btn")
    async def _handle_retry(self) -> None:
        """Handle retry button press."""
        self.notify(f"Retrying task {self._task_data.id[:8]}...")
        # TODO: Call actual retry API when available
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-btn")
    async def _handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.notify(f"Cancelling task {self._task_data.id[:8]}...")
        # TODO: Call actual cancel API when available
        self.dismiss(True)

    def action_close_modal(self) -> None:
        """Handle escape key to dismiss the modal."""
        self.dismiss(False)
