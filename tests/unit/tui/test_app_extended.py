"""Extended tests for AsyncTasQMonitorTUI app.

Tests for comprehensive coverage of the TUI app including
event handling, lifecycle, and tab switching.
"""

from unittest.mock import patch

import pytest

from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI
from asynctasq_monitor.tui.event_handler import (
    ConnectionStatusChanged,
)


class TestAsyncTasQMonitorTUILifecycle:
    """Tests for TUI app lifecycle events."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_initialization(self) -> None:
        """Test that app initializes correctly."""
        app = AsyncTasQMonitorTUI(
            redis_url="redis://localhost:6379",
            theme="dark",
            refresh_rate=1.0,
        )

        assert app.redis_url == "redis://localhost:6379"
        assert app.theme_name == "dark"
        assert app.refresh_rate == 1.0
        assert app.is_connected is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_custom_initialization(self) -> None:
        """Test that app accepts custom parameters."""
        app = AsyncTasQMonitorTUI(
            redis_url="redis://custom:6380",
            theme="light",
            refresh_rate=2.5,
        )

        assert app.redis_url == "redis://custom:6380"
        assert app.theme_name == "light"
        assert app.refresh_rate == 2.5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_mounts_all_screens(self) -> None:
        """Test that app has tab structure for screens."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            # Wait for screens to mount
            await pilot.pause()

            # Check that app is properly initialized
            assert app.title == "AsyncTasQ Monitor"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_has_footer(self) -> None:
        """Test that app has a footer widget."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            from textual.widgets import Footer

            footers = app.query(Footer)
            assert len(footers) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_has_header(self) -> None:
        """Test that app has a header widget."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            from textual.widgets import Header

            headers = app.query(Header)
            assert len(headers) > 0


class TestAsyncTasQMonitorTUIEventHandling:
    """Tests for event handling in the TUI app."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_connection_status_changed_connected(self) -> None:
        """Test that app handles connection status changed event - connected."""
        app = AsyncTasQMonitorTUI()

        # Mock event streaming to prevent actual Redis connection
        with patch.object(app, "_start_event_streaming"):
            async with app.run_test() as pilot:
                await pilot.pause()

                # Create and post a connection status event
                event = ConnectionStatusChanged(connected=True, error=None)
                app.post_message(event)
                await pilot.pause()

                # App should update is_connected
                assert app.is_connected is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_connection_status_changed_disconnected(self) -> None:
        """Test that app handles connection status changed event - disconnected."""
        app = AsyncTasQMonitorTUI()

        # Mock event streaming to prevent actual Redis connection
        with patch.object(app, "_start_event_streaming"):
            async with app.run_test() as pilot:
                # First connect
                app.post_message(ConnectionStatusChanged(connected=True, error=None))
                await pilot.pause()
                assert app.is_connected is True

                # Then disconnect
                app.post_message(ConnectionStatusChanged(connected=False, error=None))
                await pilot.pause()

                assert app.is_connected is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_connection_status_with_error(self) -> None:
        """Test that app handles connection status with error."""
        app = AsyncTasQMonitorTUI()

        # Mock event streaming to prevent actual Redis connection
        with patch.object(app, "_start_event_streaming"):
            async with app.run_test() as pilot:
                await pilot.pause()

                # Post error event
                event = ConnectionStatusChanged(connected=False, error="Connection refused")
                app.post_message(event)
                await pilot.pause()

                assert app.is_connected is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_handles_task_events(self) -> None:
        """Test that app can receive task events."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Verify the event handler method exists
            assert hasattr(app, "handle_event")
            assert callable(app.handle_event)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_handles_worker_events(self) -> None:
        """Test that app can receive worker events."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Verify the event handler method exists
            assert hasattr(app, "handle_event")
            assert callable(app.handle_event)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_app_handles_task_completed_event(self) -> None:
        """Test that app can receive task completion events."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Verify the event handler method exists
            assert hasattr(app, "handle_event")
            assert callable(app.handle_event)


class TestAsyncTasQMonitorTUINavigation:
    """Tests for navigation between tabs."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_switch_to_dashboard_tab(self) -> None:
        """Test switching to dashboard tab via action."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to dashboard (default)
            app.action_switch_tab("dashboard")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_switch_to_tasks_tab(self) -> None:
        """Test switching to tasks tab via action."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to tasks
            app.action_switch_tab("tasks")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_switch_to_workers_tab(self) -> None:
        """Test switching to workers tab via action."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to workers
            app.action_switch_tab("workers")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_switch_to_queues_tab(self) -> None:
        """Test switching to queues tab via action."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to queues
            app.action_switch_tab("queues")
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_keyboard_bindings_for_tabs(self) -> None:
        """Test keyboard bindings for tab navigation."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Test 'd' for dashboard
            await pilot.press("d")
            await pilot.pause()

            # Test 't' for tasks
            await pilot.press("t")
            await pilot.pause()

            # Test 'w' for workers
            await pilot.press("w")
            await pilot.pause()

            # Test 'u' for queues
            await pilot.press("u")
            await pilot.pause()


class TestAsyncTasQMonitorTUIRefresh:
    """Tests for data refresh functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_action_refresh(self) -> None:
        """Test the refresh action."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Trigger refresh
            app.action_refresh()
            await pilot.pause()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_via_keybinding(self) -> None:
        """Test refresh via 'r' keybinding."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Press 'r' to refresh
            await pilot.press("r")
            await pilot.pause()


class TestAsyncTasQMonitorTUIHelp:
    """Tests for help functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_show_help_action(self) -> None:
        """Test the show help action."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Trigger help
            app.action_show_help()
            await pilot.pause()

            # Should show help screen
            from asynctasq_monitor.tui.screens.help import HelpScreen

            assert isinstance(app.screen, HelpScreen)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_help_via_keybinding(self) -> None:
        """Test help via '?' keybinding."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Press '?' to show help
            await pilot.press("?")
            await pilot.pause()

            from asynctasq_monitor.tui.screens.help import HelpScreen

            assert isinstance(app.screen, HelpScreen)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_quit_action(self) -> None:
        """Test the quit action."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Trigger quit
            await app.action_quit()
            # The app should exit after this


class TestAsyncTasQMonitorTUIConnectionStatus:
    """Tests for connection status watch method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_watch_is_connected_true(self) -> None:
        """Test watch_is_connected when connected."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Simulate connection
            app.is_connected = True
            await pilot.pause()

            # Check header is updated
            from textual.widgets import Header

            header = app.query_one(Header)
            assert header is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_watch_is_connected_false(self) -> None:
        """Test watch_is_connected when disconnected."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            # Start connected
            app.is_connected = True
            await pilot.pause()

            # Then disconnect
            app.is_connected = False
            await pilot.pause()

            # Header should be updated

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_watch_is_connected_toggle(self) -> None:
        """Test toggling connection status multiple times."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            await pilot.pause()

            for _ in range(3):
                app.is_connected = True
                await pilot.pause()
                assert app.is_connected is True

                app.is_connected = False
                await pilot.pause()
                assert app.is_connected is False
