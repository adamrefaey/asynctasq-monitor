"""Metric card widget for displaying numeric metrics.

This module provides the MetricCard widget which displays a metric
with a label, icon, and large digits, with support for color variants.

Design Principles (2024-2025 Best Practices):
- Semantic color variants for different metric types
- Clear visual hierarchy with icon, label, and value
- Reactive value updates for real-time display
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Digits, Label


class MetricCard(Container):
    """A card displaying a metric with icon and large digits.

    The card shows an icon, label, and a numeric value using the Digits widget.
    Color variants indicate different metric types (warning, success, error).

    Example:
        >>> card = MetricCard("Pending", "pending", variant="warning", icon="")
        >>> card.value = 42  # Updates the displayed digits
    """

    # Reactive value that triggers digit updates
    value: reactive[int] = reactive(0)

    def __init__(
        self,
        label: str,
        card_id: str,
        variant: str = "default",
        initial_value: int = 0,
        icon: str = "",
    ) -> None:
        """Initialize the metric card.

        Args:
            label: The text label shown below the digits.
            card_id: The unique ID for this card.
            variant: Color variant (default, warning, accent, success, error).
            initial_value: Initial numeric value to display.
            icon: Icon character to display (optional).
        """
        super().__init__(id=card_id)
        self._label_text = label
        self._variant = variant
        self._initial_value = initial_value
        self._icon = icon
        self.add_class(f"metric-{variant}")

    def compose(self) -> ComposeResult:
        """Compose the metric card UI."""
        if self._icon:
            yield Label(self._icon, classes="metric-icon")
        yield Digits(str(self._initial_value), id=f"digits-{self.id}")
        yield Label(self._label_text, classes="metric-label")

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
