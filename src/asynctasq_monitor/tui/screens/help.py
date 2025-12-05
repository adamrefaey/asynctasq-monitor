"""Help screen for asynctasq-monitor TUI.

Displays keyboard shortcuts and navigation help in a modal dialog.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Static

KEYBINDINGS_TEXT = """\
[bold cyan]KEYBOARD SHORTCUTS[/]

[bold]Navigation[/]
  [green]d[/]          Go to Dashboard
  [green]t[/]          Go to Tasks
  [green]w[/]          Go to Workers
  [green]u[/]          Go to Queues

[bold]List Navigation[/]
  [green]j[/] / [green]↓[/]      Move down
  [green]k[/] / [green]↑[/]      Move up
  [green]g[/]          Go to top
  [green]G[/]          Go to bottom
  [green]Enter[/]      Open detail
  [green]/[/]          Search

[bold]Actions[/]
  [green]r[/]          Refresh data
  [green]?[/]          Show this help
  [green]q[/]          Quit
  [green]Ctrl+C[/]     Force quit
  [green]Esc[/]        Close modal
"""


class HelpScreen(ModalScreen[None]):
    """Modal screen showing keyboard shortcuts and help."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("q", "dismiss", "Close", show=False),
        Binding("?", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the help dialog."""
        with Container(id="help-dialog"):
            yield Static("AsyncTasQ Monitor Help", id="help-title")
            yield Static(KEYBINDINGS_TEXT, id="help-content")
            yield Button("Close [Esc]", variant="primary", id="help-close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press to close the dialog."""
        if event.button.id == "help-close-btn":
            self.dismiss()
