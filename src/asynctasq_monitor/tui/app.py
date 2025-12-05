"""Main Textual application for asynctasq-monitor TUI.

This module provides the AsyncTasQMonitorTUI app class, which is the
main entry point for the terminal-based monitoring interface.
"""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane


class AsyncTasQMonitorTUI(App[None]):
    """TUI Monitor for AsyncTasQ task queues.

    A keyboard-driven dashboard for monitoring tasks, workers, and queues
    directly in your terminal.
    """

    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"
    TITLE = "AsyncTasQ Monitor"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "switch_tab('dashboard')", "Dashboard", show=True),
        Binding("t", "switch_tab('tasks')", "Tasks", show=True),
        Binding("w", "switch_tab('workers')", "Workers", show=True),
        Binding("u", "switch_tab('queues')", "Queues", show=True),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "show_help", "Help"),
    ]

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        theme: str = "dark",
        refresh_rate: float = 1.0,
    ) -> None:
        """Initialize the TUI application.

        Args:
            redis_url: Redis connection URL for event streaming.
            theme: Color theme (dark/light).
            refresh_rate: Data refresh rate in seconds.
        """
        super().__init__()
        self.redis_url = redis_url
        self.theme_name = theme
        self.refresh_rate = refresh_rate

    def compose(self) -> ComposeResult:
        """Compose the application UI."""
        yield Header()
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                yield Static("📊 Dashboard - Coming Soon", id="dashboard-placeholder")
            with TabPane("Tasks", id="tasks"):
                yield Static("📋 Tasks - Coming Soon", id="tasks-placeholder")
            with TabPane("Workers", id="workers"):
                yield Static("👷 Workers - Coming Soon", id="workers-placeholder")
            with TabPane("Queues", id="queues"):
                yield Static("📬 Queues - Coming Soon", id="queues-placeholder")
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to the specified tab.

        Args:
            tab_id: The ID of the tab to switch to.
        """
        self.query_one(TabbedContent).active = tab_id

    def action_refresh(self) -> None:
        """Force refresh all data."""
        self.notify("Refreshing data...")

    def action_show_help(self) -> None:
        """Show help modal with keyboard shortcuts."""
        from asynctasq_monitor.tui.screens.help import HelpScreen

        self.push_screen(HelpScreen())
