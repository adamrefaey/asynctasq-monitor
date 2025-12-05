"""Filter bar widget for filtering task and worker lists.

This module provides the FilterBar widget which contains search input
and status/queue filter dropdowns.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Select


class FilterBar(Horizontal):
    """Filter bar with search input and dropdown filters.

    Emits FilterChanged message when any filter value changes.
    Used to filter task lists by search term, status, and queue.

    Events:
        FilterChanged: Emitted when any filter value changes.

    Example:
        >>> filter_bar = FilterBar(
        ...     statuses=["pending", "running", "completed", "failed"],
        ...     queues=["default", "high", "low"],
        ... )
    """

    class FilterChanged(Message):
        """Emitted when any filter value changes.

        Attributes:
            search: The current search input value.
            status: The currently selected status filter.
            queue: The currently selected queue filter.
        """

        def __init__(self, search: str, status: str, queue: str) -> None:
            """Initialize the message.

            Args:
                search: The current search input value.
                status: The currently selected status filter.
                queue: The currently selected queue filter.
            """
            super().__init__()
            self.search = search
            self.status = status
            self.queue = queue

    DEFAULT_CSS = """
    FilterBar {
        height: 3;
        margin: 0 1 1 1;
        padding: 0;
    }

    FilterBar > Input {
        width: 1fr;
        margin-right: 1;
    }

    FilterBar > Select {
        width: 20;
        margin-right: 1;
    }
    """

    def __init__(
        self,
        statuses: list[str] | None = None,
        queues: list[str] | None = None,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
    ) -> None:
        """Initialize the filter bar.

        Args:
            statuses: List of status values for the status dropdown.
            queues: List of queue names for the queue dropdown.
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._statuses = statuses or []
        self._queues = queues or []

    def compose(self) -> ComposeResult:
        """Compose the filter bar UI."""
        yield Input(placeholder="Search by name or ID...", id="search-input")
        yield Select[str](
            [(s, s) for s in ["All Status", *self._statuses]],
            id="status-filter",
            value="All Status",
            allow_blank=False,
        )
        yield Select[str](
            [(q, q) for q in ["All Queues", *self._queues]],
            id="queue-filter",
            value="All Queues",
            allow_blank=False,
        )

    def _emit_filter_changed(self) -> None:
        """Emit a FilterChanged message with current filter values."""
        search_input = self.query_one("#search-input", Input)
        status_select = self.query_one("#status-filter", Select)
        queue_select = self.query_one("#queue-filter", Select)

        # Get values safely (Select.value can be Select.BLANK)
        status_value = (
            str(status_select.value) if status_select.value != Select.BLANK else "All Status"
        )
        queue_value = (
            str(queue_select.value) if queue_select.value != Select.BLANK else "All Queues"
        )

        self.post_message(
            self.FilterChanged(
                search=search_input.value,
                status=status_value,
                queue=queue_value,
            )
        )

    @on(Input.Changed, "#search-input")
    def _on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        event.stop()
        self._emit_filter_changed()

    @on(Select.Changed, "#status-filter")
    def _on_status_changed(self, event: Select.Changed) -> None:
        """Handle status filter changes."""
        event.stop()
        self._emit_filter_changed()

    @on(Select.Changed, "#queue-filter")
    def _on_queue_changed(self, event: Select.Changed) -> None:
        """Handle queue filter changes."""
        event.stop()
        self._emit_filter_changed()

    def reset_filters(self) -> None:
        """Reset all filters to default values."""
        self.query_one("#search-input", Input).value = ""
        self.query_one("#status-filter", Select).value = "All Status"
        self.query_one("#queue-filter", Select).value = "All Queues"
