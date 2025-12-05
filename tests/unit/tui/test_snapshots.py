"""Snapshot tests for TUI screens.

These tests use pytest-textual-snapshot to capture and compare
visual snapshots of the TUI screens. This helps catch visual
regressions in the UI layout and styling.

Usage:
    # Run snapshot tests
    pytest tests/unit/tui/test_snapshots.py -v

    # Update snapshots after verifying changes are correct
    pytest tests/unit/tui/test_snapshots.py --snapshot-update
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


# Mark all tests in this module as requiring snapshot testing
pytestmark = [pytest.mark.unit, pytest.mark.snapshot]


class TestDashboardSnapshots:
    """Snapshot tests for the Dashboard screen."""

    def test_dashboard_initial_render(self, snap_compare: SnapshotAssertion) -> None:
        """Test that the dashboard renders correctly on initial load."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        async def run_before(pilot: object) -> None:
            """Wait for initial render to complete."""
            await pilot.pause()  # type: ignore[attr-defined]

        # Mock event streaming to prevent Redis connection
        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                run_before=run_before,
                terminal_size=(120, 40),
            )

    def test_dashboard_with_metrics(self, snap_compare: SnapshotAssertion) -> None:
        """Test dashboard with populated metrics."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI
        from asynctasq_monitor.tui.screens.dashboard import DashboardScreen

        async def run_before(pilot: object) -> None:
            """Set up dashboard with sample metrics."""
            await pilot.pause()  # type: ignore[attr-defined]
            app = pilot.app  # type: ignore[attr-defined]
            try:
                dashboard = app.query_one("#dashboard-screen", DashboardScreen)
                dashboard.update_metrics(pending=42, running=5, completed=1234, failed=12)
            except Exception:
                pass  # Dashboard may not be mounted yet

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                run_before=run_before,
                terminal_size=(120, 40),
            )


class TestTasksSnapshots:
    """Snapshot tests for the Tasks screen."""

    def test_tasks_screen_initial(self, snap_compare: SnapshotAssertion) -> None:
        """Test that the tasks screen renders correctly."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                press=["t"],  # Switch to tasks tab
                terminal_size=(120, 40),
            )


class TestWorkersSnapshots:
    """Snapshot tests for the Workers screen."""

    def test_workers_screen_initial(self, snap_compare: SnapshotAssertion) -> None:
        """Test that the workers screen renders correctly."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                press=["w"],  # Switch to workers tab
                terminal_size=(120, 40),
            )


class TestQueuesSnapshots:
    """Snapshot tests for the Queues screen."""

    def test_queues_screen_initial(self, snap_compare: SnapshotAssertion) -> None:
        """Test that the queues screen renders correctly."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                press=["u"],  # Switch to queues tab
                terminal_size=(120, 40),
            )


class TestHelpSnapshots:
    """Snapshot tests for the Help modal."""

    def test_help_modal_render(self, snap_compare: SnapshotAssertion) -> None:
        """Test that the help modal renders correctly."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                press=["?"],  # Open help modal
                terminal_size=(120, 40),
            )


class TestNavigationSnapshots:
    """Snapshot tests for navigation between screens."""

    def test_tab_navigation_sequence(self, snap_compare: SnapshotAssertion) -> None:
        """Test navigating through all tabs."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            # Navigate through tabs: dashboard -> tasks -> workers -> queues -> dashboard
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                press=["t", "w", "u", "d"],
                terminal_size=(120, 40),
            )


class TestResponsiveSnapshots:
    """Snapshot tests for different terminal sizes."""

    def test_dashboard_small_terminal(self, snap_compare: SnapshotAssertion) -> None:
        """Test dashboard renders correctly in a small terminal."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                terminal_size=(80, 24),  # Smaller terminal
            )

    def test_dashboard_wide_terminal(self, snap_compare: SnapshotAssertion) -> None:
        """Test dashboard renders correctly in a wide terminal."""
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI

        with patch.object(AsyncTasQMonitorTUI, "_start_event_streaming"):
            assert snap_compare(
                AsyncTasQMonitorTUI(),
                terminal_size=(160, 50),  # Larger terminal
            )
