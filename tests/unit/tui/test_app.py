"""Tests for TUI application.

Tests for the Textual-based terminal UI.
"""

import pytest

from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI


class TestAsyncTasQMonitorTUI:
    """Tests for the main TUI application."""

    @pytest.mark.unit
    def test_app_instantiation(self) -> None:
        """Test that the TUI app can be instantiated."""
        app = AsyncTasQMonitorTUI()
        assert app.redis_url == "redis://localhost:6379"
        assert app.theme_name == "dark"
        assert app.refresh_rate == 1.0

    @pytest.mark.unit
    def test_app_instantiation_with_custom_params(self) -> None:
        """Test TUI app with custom parameters."""
        app = AsyncTasQMonitorTUI(
            redis_url="redis://custom:6380",
            theme="light",
            refresh_rate=2.5,
        )
        assert app.redis_url == "redis://custom:6380"
        assert app.theme_name == "light"
        assert app.refresh_rate == 2.5

    @pytest.mark.unit
    def test_app_has_bindings(self) -> None:
        """Test that the app has expected key bindings."""
        from textual.binding import Binding

        app = AsyncTasQMonitorTUI()
        binding_keys: list[str] = []
        for b in app.BINDINGS:
            if isinstance(b, Binding):
                binding_keys.append(b.key)
            else:
                # It's a tuple (key, action, description)
                binding_keys.append(b[0])

        assert "q" in binding_keys  # Quit
        assert "d" in binding_keys  # Dashboard
        assert "t" in binding_keys  # Tasks
        assert "w" in binding_keys  # Workers
        assert "u" in binding_keys  # Queues
        assert "r" in binding_keys  # Refresh
        assert "?" in binding_keys  # Help

    @pytest.mark.unit
    def test_app_title(self) -> None:
        """Test that the app has the expected title."""
        app = AsyncTasQMonitorTUI()
        assert app.TITLE == "AsyncTasQ Monitor"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_compose(self) -> None:
        """Test that the app composes correctly."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()
            # Check that main components are present
            assert app.query_one("Header") is not None
            assert app.query_one("Footer") is not None
            assert app.query_one("TabbedContent") is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_has_dashboard_screen(self) -> None:
        """Test that the app has DashboardScreen in the dashboard tab."""
        from asynctasq_monitor.tui.screens.dashboard import DashboardScreen

        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()
            # Check dashboard screen exists
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)
            assert dashboard is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_has_tabs(self) -> None:
        """Test that the app has all expected tabs."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()
            # Check tab panes exist
            assert app.query_one("#dashboard") is not None
            assert app.query_one("#tasks") is not None
            assert app.query_one("#workers") is not None
            assert app.query_one("#queues") is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_switch_tab_action(self) -> None:
        """Test that switching tabs works."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import TabbedContent

            tabbed_content = app.query_one(TabbedContent)

            # Initial tab should be dashboard
            assert tabbed_content.active == "dashboard"

            # Switch to tasks
            app.action_switch_tab("tasks")
            assert tabbed_content.active == "tasks"

            # Switch to workers
            app.action_switch_tab("workers")
            assert tabbed_content.active == "workers"

            # Switch to queues
            app.action_switch_tab("queues")
            assert tabbed_content.active == "queues"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_help_screen_opens(self) -> None:
        """Test that the help screen opens correctly."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            # Press ? to open help
            await pilot.press("?")

            # Check that help screen is now active
            from asynctasq_monitor.tui.screens.help import HelpScreen

            assert isinstance(app.screen, HelpScreen)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_help_screen_closes_on_escape(self) -> None:
        """Test that the help screen closes on Escape."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            # Open help
            await pilot.press("?")

            from asynctasq_monitor.tui.screens.help import HelpScreen

            assert isinstance(app.screen, HelpScreen)

            # Close with Escape
            await pilot.press("escape")

            # Should be back to main screen
            assert not isinstance(app.screen, HelpScreen)


class TestAsyncTasQMonitorTUIEventHandling:
    """Tests for event handling in the TUI application."""

    @pytest.mark.unit
    def test_app_has_metrics_tracker(self) -> None:
        """Test that the app has a metrics tracker."""
        app = AsyncTasQMonitorTUI()
        assert app._metrics_tracker is not None
        assert app._metrics_tracker.pending == 0

    @pytest.mark.unit
    def test_app_has_event_consumer_attribute(self) -> None:
        """Test that the app has event consumer attribute."""
        app = AsyncTasQMonitorTUI()
        assert app._event_consumer is None  # Not started yet

    @pytest.mark.unit
    def test_app_has_connected_reactive(self) -> None:
        """Test that the app has is_connected reactive attribute."""
        app = AsyncTasQMonitorTUI()
        assert app.is_connected is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_status_updates_subtitle(self) -> None:
        """Test that connection status updates the subtitle."""
        from unittest.mock import patch

        from asynctasq_monitor.tui.event_handler import ConnectionStatusChanged

        app = AsyncTasQMonitorTUI()

        # Mock the event streaming to prevent actual Redis connection
        with patch.object(app, "_start_event_streaming"):
            async with app.run_test() as pilot:
                await pilot.pause()

                # Without event streaming, should be disconnected initially
                assert app.is_connected is False
                assert "Disconnected" in app.sub_title

                # Simulate connection status change
                app.post_message(ConnectionStatusChanged(connected=True))
                await pilot.pause()

                assert app.is_connected is True
                assert "Connected" in app.sub_title

                # Simulate disconnection
                app.post_message(ConnectionStatusChanged(connected=False, error="Lost connection"))
                await pilot.pause()

                assert app.is_connected is False
                assert "Disconnected" in app.sub_title

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_event_updates_dashboard_metrics(self) -> None:
        """Test that events update dashboard metrics."""
        from asynctasq_monitor.tui.event_handler import (
            EventReceived,
            TUIEvent,
            TUIEventType,
        )

        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Create a task enqueued event
            event = TUIEvent(
                type=TUIEventType.TASK_ENQUEUED,
                data={"task_id": "test123", "task_name": "send_email", "queue": "default"},
            )
            app.post_message(EventReceived(event))
            await pilot.pause()

            # Check metrics tracker was updated
            assert app._metrics_tracker.pending == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_events_update_metrics(self) -> None:
        """Test multiple events update metrics correctly."""
        from asynctasq_monitor.tui.event_handler import (
            EventReceived,
            TUIEvent,
            TUIEventType,
        )

        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Enqueue 3 tasks
            for i in range(3):
                event = TUIEvent(
                    type=TUIEventType.TASK_ENQUEUED,
                    data={"task_id": f"task{i}", "task_name": "test", "queue": "default"},
                )
                app.post_message(EventReceived(event))

            await pilot.pause()
            assert app._metrics_tracker.pending == 3

            # Start 2 tasks
            for i in range(2):
                event = TUIEvent(
                    type=TUIEventType.TASK_STARTED,
                    data={"task_id": f"task{i}", "task_name": "test"},
                )
                app.post_message(EventReceived(event))

            await pilot.pause()
            assert app._metrics_tracker.pending == 1
            assert app._metrics_tracker.running == 2

            # Complete 1 task
            event = TUIEvent(
                type=TUIEventType.TASK_COMPLETED,
                data={"task_id": "task0", "task_name": "test"},
            )
            app.post_message(EventReceived(event))

            await pilot.pause()
            assert app._metrics_tracker.running == 1
            assert app._metrics_tracker.completed == 1
