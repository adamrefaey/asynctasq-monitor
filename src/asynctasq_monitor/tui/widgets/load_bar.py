"""Worker load bar widget for displaying resource usage.

This module provides the LoadBar widget which displays a progress-style
bar for visualizing worker CPU/memory load with color-coded thresholds.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar


class LoadBar(Horizontal):
    """A compact horizontal bar showing resource utilization.

    Displays a label and a progress bar that changes color based on
    load thresholds: green (low), yellow (medium), red (high).

    Example:
        >>> load_bar = LoadBar("CPU", max_val=100)
        >>> load_bar.value = 75  # Updates the bar to 75%
    """

    # Reactive value that triggers bar updates
    value: reactive[int] = reactive(0)

    # Load thresholds for color coding (percentage)
    THRESHOLD_LOW: int = 50
    THRESHOLD_HIGH: int = 80

    DEFAULT_CSS = """
    LoadBar {
        height: 1;
        width: 100%;
        margin: 0;
        padding: 0;
    }

    LoadBar .load-label {
        width: 10;
        text-align: right;
        padding-right: 1;
    }

    LoadBar ProgressBar {
        width: 1fr;
        padding: 0;
    }

    LoadBar.load-low ProgressBar Bar > .bar--bar {
        color: $success;
    }

    LoadBar.load-medium ProgressBar Bar > .bar--bar {
        color: $warning;
    }

    LoadBar.load-high ProgressBar Bar > .bar--bar {
        color: $error;
    }
    """

    def __init__(
        self,
        label: str,
        max_val: int = 100,
        initial_value: int = 0,
        bar_id: str | None = None,
    ) -> None:
        """Initialize the load bar widget.

        Args:
            label: The text label shown before the bar (e.g., "CPU", "Memory").
            max_val: Maximum value for the progress bar (default 100 for percentage).
            initial_value: Initial value to display.
            bar_id: Optional ID for the widget.
        """
        super().__init__(id=bar_id)
        self._label_text = label
        self._max_val = max_val
        self._initial_value = initial_value
        # Set initial load class
        self._update_load_class(initial_value)

    def compose(self) -> ComposeResult:
        """Compose the load bar UI."""
        yield Label(f"{self._label_text}:", classes="load-label")
        yield ProgressBar(total=self._max_val, show_percentage=True, show_eta=False)

    def on_mount(self) -> None:
        """Set initial value when mounted."""
        self.value = self._initial_value

    def watch_value(self, new_value: int) -> None:
        """Update progress bar when value changes.

        Args:
            new_value: The new load value.
        """
        # Update the progress bar
        bar = self.query_one(ProgressBar)
        bar.update(progress=new_value)

        # Update color class based on threshold
        self._update_load_class(new_value)

    def _update_load_class(self, load_value: int) -> None:
        """Update CSS class based on load value for color coding.

        Args:
            load_value: Current load percentage value.
        """
        # Calculate percentage if max_val is not 100
        percentage = (load_value / self._max_val) * 100 if self._max_val > 0 else 0

        # Remove existing load classes
        self.remove_class("load-low", "load-medium", "load-high")

        # Add appropriate class based on thresholds
        if percentage >= self.THRESHOLD_HIGH:
            self.add_class("load-high")
        elif percentage >= self.THRESHOLD_LOW:
            self.add_class("load-medium")
        else:
            self.add_class("load-low")

    @property
    def percentage(self) -> float:
        """Get current load as a percentage.

        Returns:
            Current load value as a percentage (0-100).
        """
        return (self.value / self._max_val) * 100 if self._max_val > 0 else 0.0
