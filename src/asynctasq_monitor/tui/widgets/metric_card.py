"""Metric card widget for displaying numeric metrics.

This module provides the MetricCard widget which displays a metric
with a label and large digits, with support for color variants.
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Digits, Label


class MetricCard(Container):
    """A card displaying a metric with large digits.

    The card shows a label and a numeric value using the Digits widget.
    Color variants can be used to indicate different metric types.

    Example:
        >>> card = MetricCard("Pending", "pending", variant="warning")
        >>> card.value = 42  # Updates the displayed digits
    """

    # Reactive value that triggers digit updates
    value: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    MetricCard {
        width: 1fr;
        height: 100%;
        margin: 0 1;
        padding: 1 2;
        background: $panel;
        border: solid $primary;
    }

    MetricCard .metric-label {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    MetricCard Digits {
        text-align: center;
        width: 100%;
    }

    MetricCard.metric-warning Digits {
        color: $warning;
    }

    MetricCard.metric-accent Digits {
        color: $accent;
    }

    MetricCard.metric-success Digits {
        color: $success;
    }

    MetricCard.metric-error Digits {
        color: $error;
    }

    MetricCard.metric-default Digits {
        color: $text;
    }
    """

    def __init__(
        self,
        label: str,
        card_id: str,
        variant: str = "default",
        initial_value: int = 0,
    ) -> None:
        """Initialize the metric card.

        Args:
            label: The text label shown above the digits.
            card_id: The unique ID for this card.
            variant: Color variant (default, warning, accent, success, error).
            initial_value: Initial numeric value to display.
        """
        super().__init__(id=card_id)
        self._label_text = label
        self._variant = variant
        self._initial_value = initial_value
        self.add_class(f"metric-{variant}")

    def compose(self) -> ComposeResult:
        """Compose the metric card UI."""
        yield Label(self._label_text, classes="metric-label")
        yield Digits(str(self._initial_value), id=f"digits-{self.id}")

    def on_mount(self) -> None:
        """Set initial value when mounted."""
        self.value = self._initial_value

    def watch_value(self, new_value: int) -> None:
        """Update digits when value changes.

        Args:
            new_value: The new value to display.
        """
        try:
            digits = self.query_one(Digits)
            digits.update(str(new_value))
        except Exception:
            # Widget may not be mounted yet
            pass
