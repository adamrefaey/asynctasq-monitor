"""Main Textual application for asynctasq-monitor TUI.

This module provides the AsyncTasQMonitorTUI app class, which is the
main entry point for the terminal-based monitoring interface.

Real-time Update Architecture:
    1. TUIEventConsumer subscribes to Redis Pub/Sub channel
    2. Events are deserialized and posted as Textual Messages
    3. App handles messages and updates reactive attributes
    4. Watch methods on screens automatically update the UI

Best Practices (2024-2025):
    - Uses @work decorator for non-blocking background tasks
    - Uses reactive attributes for automatic UI updates
    - Proper cleanup on app shutdown
    - Thread-safe UI updates via message passing
"""

import logging
from pathlib import Path
from time import monotonic

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header, TabbedContent, TabPane

from asynctasq_monitor.tui.event_handler import (
    ConnectionStatusChanged,
    EventReceived,
    MetricsTracker,
    TUIEvent,
    TUIEventConsumer,
    TUIEventType,
)
from asynctasq_monitor.tui.screens.dashboard import DashboardScreen
from asynctasq_monitor.tui.screens.queues import QueuesScreen
from asynctasq_monitor.tui.screens.tasks import TasksScreen
from asynctasq_monitor.tui.screens.workers import WorkersScreen

logger = logging.getLogger(__name__)


class AsyncTasQMonitorTUI(App[None]):
    """TUI Monitor for AsyncTasQ task queues.

    A keyboard-driven dashboard for monitoring tasks, workers, and queues
    directly in your terminal. Features real-time updates via Redis Pub/Sub.

    Attributes:
        redis_url: Redis connection URL for event streaming.
        theme_name: Color theme (dark/light).
        refresh_rate: Data refresh rate in seconds.
        is_connected: Whether connected to Redis for events.
    """

    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"
    TITLE = "AsyncTasQ Monitor"

    # Reactive connection status for UI feedback
    is_connected: reactive[bool] = reactive(False)

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

        # Event consumer and metrics tracking
        self._event_consumer: TUIEventConsumer | None = None
        self._metrics_tracker = MetricsTracker()
        self._throughput_timer_handle: object | None = None

    def compose(self) -> ComposeResult:
        """Compose the application UI."""
        yield Header()
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                yield DashboardScreen(id="dashboard-screen")
            with TabPane("Tasks", id="tasks"):
                yield TasksScreen(id="tasks-screen")
            with TabPane("Workers", id="workers"):
                yield WorkersScreen(id="workers-screen")
            with TabPane("Queues", id="queues"):
                yield QueuesScreen(id="queues-screen")
        yield Footer()

    async def on_mount(self) -> None:
        """Start event streaming when the app mounts."""
        # Start the event consumer in the background
        self._start_event_streaming()

        # Start throughput sampling timer
        self._throughput_timer_handle = self.set_interval(
            self.refresh_rate, self._sample_throughput, name="throughput_sampler"
        )

    async def on_unmount(self) -> None:
        """Cleanup resources when the app unmounts."""
        await self._stop_event_streaming()

    @work(exclusive=True, name="event_streamer")
    async def _start_event_streaming(self) -> None:
        """Start consuming events from Redis in a background worker.

        Uses the @work decorator to run without blocking the UI.
        The exclusive=True ensures only one consumer runs at a time.
        """
        try:
            self._event_consumer = TUIEventConsumer(
                app=self,
                redis_url=self.redis_url,
            )
            await self._event_consumer.start()
        except Exception as e:
            logger.exception("Failed to start event streaming")
            self.notify(f"Event streaming failed: {e}", severity="error", timeout=5)

    async def _stop_event_streaming(self) -> None:
        """Stop the event consumer gracefully."""
        if self._event_consumer is not None:
            await self._event_consumer.stop()
            self._event_consumer = None

    def _sample_throughput(self) -> None:
        """Sample throughput and update the dashboard sparkline."""
        sample = self._metrics_tracker.sample_throughput(monotonic())
        if sample is not None:
            try:
                dashboard = self.query_one("#dashboard-screen", DashboardScreen)
                dashboard.add_throughput_sample(sample)
            except Exception:
                pass  # Dashboard not mounted

    @on(ConnectionStatusChanged)
    def handle_connection_status(self, event: ConnectionStatusChanged) -> None:
        """Handle Redis connection status changes.

        Args:
            event: The connection status change event.
        """
        self.is_connected = event.connected
        if event.connected:
            self.notify("Connected to Redis", severity="information", timeout=3)
        elif event.error:
            self.notify(f"Redis connection error: {event.error}", severity="error", timeout=5)
        else:
            self.notify("Disconnected from Redis", severity="warning", timeout=3)

    @on(EventReceived)
    def handle_event(self, message: EventReceived) -> None:
        """Handle incoming events from Redis and update the UI.

        This method is the central event dispatcher. It updates the metrics
        tracker and then dispatches to specific handlers based on event type.

        Args:
            message: The event message from Redis.
        """
        event = message.event
        self._metrics_tracker.handle_event(event)

        # Update dashboard metrics
        try:
            dashboard = self.query_one("#dashboard-screen", DashboardScreen)
            dashboard.update_metrics(
                pending=self._metrics_tracker.pending,
                running=self._metrics_tracker.running,
                completed=self._metrics_tracker.completed,
                failed=self._metrics_tracker.failed,
            )
        except Exception:
            pass  # Dashboard not mounted yet

        # Update activity log
        self._update_activity_log(event)

        # Dispatch to screen-specific handlers
        match event.type:
            case (
                TUIEventType.TASK_ENQUEUED
                | TUIEventType.TASK_STARTED
                | TUIEventType.TASK_COMPLETED
                | TUIEventType.TASK_FAILED
                | TUIEventType.TASK_RETRYING
            ):
                self._handle_task_event(event)
            case (
                TUIEventType.WORKER_ONLINE
                | TUIEventType.WORKER_HEARTBEAT
                | TUIEventType.WORKER_OFFLINE
            ):
                self._handle_worker_event(event)

    def _handle_task_event(self, event: TUIEvent) -> None:
        """Handle task-related events.

        Notifies the tasks screen to refresh its data when task events occur.
        This ensures the task list stays in sync with real-time events.

        Args:
            event: The task event.
        """
        try:
            # Notify tasks screen to refresh on task events
            tasks_screen = self.query_one("#tasks-screen", TasksScreen)
            # Trigger a refresh of the task list
            tasks_screen._refresh_tasks_from_backend()
        except Exception:
            pass  # Tasks screen not mounted

    def _handle_worker_event(self, event: TUIEvent) -> None:
        """Handle worker-related events.

        Updates the workers table with new worker state.

        Args:
            event: The worker event.
        """
        # Future: Update workers table with new worker data
        pass

    def _update_activity_log(self, event: TUIEvent) -> None:
        """Update the recent activity display on the dashboard.

        Args:
            event: The event to log.
        """
        try:
            dashboard = self.query_one("#dashboard-screen", DashboardScreen)

            # Format activity message based on event type with timestamp
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            activity_lines: list[str] = []

            match event.type:
                case TUIEventType.TASK_ENQUEUED:
                    task_name = event.task_name or "unknown"
                    queue = event.queue or "default"
                    activity_lines.append(f"[{timestamp}]  {task_name} -> {queue}")
                case TUIEventType.TASK_STARTED:
                    task_name = event.task_name or "unknown"
                    worker = (event.worker_id or "?")[:8]
                    activity_lines.append(f"[{timestamp}]  {task_name} @ {worker}")
                case TUIEventType.TASK_COMPLETED:
                    task_name = event.task_name or "unknown"
                    duration_ms = event.data.get("duration_ms")
                    duration_str = f" ({duration_ms}ms)" if duration_ms else ""
                    activity_lines.append(f"[{timestamp}]  {task_name}{duration_str}")
                case TUIEventType.TASK_FAILED:
                    task_name = event.task_name or "unknown"
                    error = event.data.get("error", "error")
                    if len(error) > 30:
                        error = error[:27] + "..."
                    activity_lines.append(f"[{timestamp}]  {task_name}: {error}")
                case TUIEventType.TASK_RETRYING:
                    task_name = event.task_name or "unknown"
                    attempt = event.data.get("attempt", 1)
                    activity_lines.append(f"[{timestamp}]  {task_name} (#{attempt})")
                case TUIEventType.WORKER_ONLINE:
                    worker = (event.worker_id or "?")[:12]
                    activity_lines.append(f"[{timestamp}]  Worker {worker}")
                case TUIEventType.WORKER_OFFLINE:
                    worker = (event.worker_id or "?")[:12]
                    activity_lines.append(f"[{timestamp}]  Worker {worker}")

            if activity_lines:
                # Get current activity widget
                try:
                    activity_widget = dashboard.query_one("#activity-log")
                    current_text = str(activity_widget.render())
                    if current_text in ("Waiting for events...", "No recent activity"):
                        current_text = ""

                    # Keep last 15 activity lines for better visibility
                    current_lines = [line for line in current_text.split("\n") if line.strip()]
                    new_lines = activity_lines + current_lines
                    new_lines = new_lines[:15]

                    dashboard.update_activity("\n".join(new_lines))
                except Exception:
                    pass

        except Exception:
            pass  # Dashboard not mounted

    def watch_is_connected(self, connected: bool) -> None:
        """Update UI when connection status changes.

        Updates the header subtitle to show connection status with
        clear visual indicators.

        Args:
            connected: Whether connected to Redis.
        """
        if connected:
            self.sub_title = "Connected to Redis"
        else:
            self.sub_title = "Disconnected"

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to the specified tab.

        Args:
            tab_id: The ID of the tab to switch to.
        """
        self.query_one(TabbedContent).active = tab_id

    def action_refresh(self) -> None:
        """Force refresh all data.

        This triggers a manual data refresh from Redis/API,
        useful when real-time events may have been missed.
        """
        self.notify("Refreshing data...")
        self._refresh_all_data()

    @work(exclusive=True, name="data_refresher")
    async def _refresh_all_data(self) -> None:
        """Refresh all data from the backend.

        This is a manual refresh that fetches current state from Redis,
        useful for initial load or when events may have been missed.
        """
        # TODO: Implement API/Redis calls to refresh data
        # For now, just notify completion
        self.notify("Data refreshed", timeout=2)

    def action_show_help(self) -> None:
        """Show help modal with keyboard shortcuts."""
        from asynctasq_monitor.tui.screens.help import HelpScreen

        self.push_screen(HelpScreen())
