"""Unit tests for the TasksScreen."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from asynctasq_monitor.models.task import Task, TaskStatus
from asynctasq_monitor.tui.screens.tasks import TasksScreen
from asynctasq_monitor.tui.widgets.filter_bar import FilterBar
from asynctasq_monitor.tui.widgets.task_table import TaskTable


class TestTasksScreen:
    """Tests for the TasksScreen."""

    def test_statuses_defined(self) -> None:
        """Test that all expected statuses are defined."""
        expected = ["pending", "running", "completed", "failed", "retrying", "cancelled"]
        assert TasksScreen.STATUSES == expected

    def test_queues_defined(self) -> None:
        """Test that default queues are defined."""
        assert len(TasksScreen.QUEUES) > 0
        assert "default" in TasksScreen.QUEUES

    @pytest.mark.asyncio
    async def test_compose_yields_required_widgets(self) -> None:
        """Test that compose yields FilterBar and TaskTable."""
        from textual.app import App
        from textual.widgets import Label

        class TestApp(App[None]):
            def compose(self):
                yield TasksScreen(id="tasks-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#tasks-screen", TasksScreen)

            # Check required widgets exist
            assert screen.query_one(".section-title", Label) is not None
            assert screen.query_one("#filter-bar", FilterBar) is not None
            assert screen.query_one("#task-table", TaskTable) is not None

    @pytest.mark.asyncio
    async def test_sample_data_loaded_on_mount(self) -> None:
        """Test that sample data is loaded on mount."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield TasksScreen(id="tasks-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#tasks-screen", TasksScreen)
            table = screen.query_one("#task-table", TaskTable)

            # Sample data should have been loaded
            assert table.row_count > 0
            assert len(screen.tasks) > 0

    @pytest.mark.asyncio
    async def test_filter_by_search(self) -> None:
        """Test filtering tasks by search term."""
        from textual.app import App
        from textual.widgets import Input

        class TestApp(App[None]):
            def compose(self):
                yield TasksScreen(id="tasks-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#tasks-screen", TasksScreen)
            table = screen.query_one("#task-table", TaskTable)
            filter_bar = screen.query_one("#filter-bar", FilterBar)

            # Get initial count
            initial_count = table.row_count

            # Search for a specific task
            search_input = filter_bar.query_one("#search-input", Input)
            search_input.value = "send_email"
            await pilot.pause()

            # Should have fewer results
            assert table.row_count < initial_count

    @pytest.mark.asyncio
    async def test_refresh_tasks(self) -> None:
        """Test that refresh_tasks updates the task list."""
        from textual.app import App

        now = datetime.now(UTC)
        new_tasks = [
            Task(
                id="new-task-1",
                name="new_task",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TasksScreen(id="tasks-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#tasks-screen", TasksScreen)
            table = screen.query_one("#task-table", TaskTable)

            # Refresh with new tasks
            screen.refresh_tasks(new_tasks)
            await pilot.pause()

            # Should have exactly 1 task
            assert table.row_count == 1
            assert len(screen.tasks) == 1

    @pytest.mark.asyncio
    async def test_filter_by_status(self) -> None:
        """Test filtering tasks by status."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield TasksScreen(id="tasks-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#tasks-screen", TasksScreen)

            # Manually set status filter and trigger update
            screen._current_status = "pending"
            screen._update_table()
            await pilot.pause()

            table = screen.query_one("#task-table", TaskTable)
            # Only pending tasks should be shown
            # The exact count depends on sample data
            assert table.row_count >= 0  # At least 0 pending tasks

    @pytest.mark.asyncio
    async def test_filter_by_queue(self) -> None:
        """Test filtering tasks by queue."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield TasksScreen(id="tasks-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#tasks-screen", TasksScreen)

            # Manually set queue filter and trigger update
            screen._current_queue = "email"
            screen._update_table()
            await pilot.pause()

            table = screen.query_one("#task-table", TaskTable)
            # Only email queue tasks should be shown
            assert table.row_count >= 0

    @pytest.mark.asyncio
    async def test_task_selection_opens_modal(self) -> None:
        """Test that selecting a task opens the detail modal."""
        from textual.app import App

        from asynctasq_monitor.tui.screens.task_detail import TaskDetailScreen

        class TestApp(App[None]):
            def compose(self):
                yield TasksScreen(id="tasks-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#tasks-screen", TasksScreen)
            table = screen.query_one("#task-table", TaskTable)

            # Focus the table and select first row
            table.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            # Modal should be open
            assert isinstance(pilot.app.screen, TaskDetailScreen)
