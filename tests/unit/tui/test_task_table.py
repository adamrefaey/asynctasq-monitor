"""Unit tests for the TaskTable widget."""

from datetime import UTC, datetime

import pytest
from rich.text import Text

from asynctasq_monitor.models.task import Task, TaskStatus
from asynctasq_monitor.tui.widgets.task_table import TaskTable


class TestTaskTable:
    """Tests for the TaskTable widget."""

    def test_status_styles_defined(self) -> None:
        """Test that all task statuses have styles (color and icon) defined."""
        for status in TaskStatus:
            assert status.value in TaskTable.STATUS_STYLES, f"Missing style for {status.value}"
            color, icon = TaskTable.STATUS_STYLES[status.value]
            assert isinstance(color, str), f"Color for {status.value} should be a string"
            assert isinstance(icon, str), f"Icon for {status.value} should be a string"

    def test_task_selected_message(self) -> None:
        """Test TaskSelected message initialization."""
        msg = TaskTable.TaskSelected("test-task-id")
        assert msg.task_id == "test-task-id"

    @pytest.mark.asyncio
    async def test_table_mounts_with_columns(self) -> None:
        """Test that table has correct columns after mounting."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            assert table is not None

            # Check columns exist
            columns = list(table.columns.keys())
            assert len(columns) == 6

    @pytest.mark.asyncio
    async def test_table_cursor_type_is_row(self) -> None:
        """Test that table cursor type is set to row."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            assert table.cursor_type == "row"

    @pytest.mark.asyncio
    async def test_table_has_zebra_stripes(self) -> None:
        """Test that table has zebra stripes enabled."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            assert table.zebra_stripes is True

    @pytest.mark.asyncio
    async def test_update_tasks_populates_table(self) -> None:
        """Test that update_tasks populates the table with data."""
        from textual.app import App

        now = datetime.now(UTC)
        tasks = [
            Task(
                id="task-1-1234-5678-9abc",
                name="test_task_1",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
            Task(
                id="task-2-1234-5678-9abc",
                name="test_task_2",
                queue="high",
                status=TaskStatus.RUNNING,
                enqueued_at=now,
                worker_id="worker-123",
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_update_tasks_clears_existing_rows(self) -> None:
        """Test that update_tasks clears existing rows before adding new ones."""
        from textual.app import App

        now = datetime.now(UTC)

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)

            # Add first batch
            tasks1 = [
                Task(
                    id="task-1",
                    name="test1",
                    queue="default",
                    status=TaskStatus.PENDING,
                    enqueued_at=now,
                )
            ]
            table.update_tasks(tasks1)
            await pilot.pause()
            assert table.row_count == 1

            # Add second batch (should replace, not append)
            tasks2 = [
                Task(
                    id="task-2",
                    name="test2",
                    queue="high",
                    status=TaskStatus.RUNNING,
                    enqueued_at=now,
                ),
                Task(
                    id="task-3",
                    name="test3",
                    queue="low",
                    status=TaskStatus.COMPLETED,
                    enqueued_at=now,
                ),
            ]
            table.update_tasks(tasks2)
            await pilot.pause()
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_status_colors_applied(self) -> None:
        """Test that status colors are applied correctly."""
        from textual.app import App

        now = datetime.now(UTC)
        tasks = [
            Task(
                id="task-1",
                name="pending_task",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            # Get the row data
            row = table.get_row_at(0)
            # Status column (index 3) should be a styled Text object with icon
            assert isinstance(row[3], Text)
            assert "pending" in str(row[3])  # Status now includes icon prefix

    @pytest.mark.asyncio
    async def test_worker_id_truncated(self) -> None:
        """Test that long worker IDs are truncated."""
        from textual.app import App

        now = datetime.now(UTC)
        tasks = [
            Task(
                id="task-1",
                name="running_task",
                queue="default",
                status=TaskStatus.RUNNING,
                enqueued_at=now,
                worker_id="worker-1234567890-abcdef",
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            row = table.get_row_at(0)
            # Worker column (index 4) should be truncated to 8 chars (now returns Text)
            assert len(str(row[4])) == 8

    @pytest.mark.asyncio
    async def test_missing_worker_shows_dash(self) -> None:
        """Test that missing worker ID shows dash."""
        from textual.app import App

        now = datetime.now(UTC)
        tasks = [
            Task(
                id="task-1",
                name="pending_task",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            row = table.get_row_at(0)
            # Now returns Text object
            assert str(row[4]) == "-"

    @pytest.mark.asyncio
    async def test_duration_formatted(self) -> None:
        """Test that duration is formatted correctly."""
        from textual.app import App

        now = datetime.now(UTC)
        tasks = [
            Task(
                id="task-1",
                name="completed_task",
                queue="default",
                status=TaskStatus.COMPLETED,
                enqueued_at=now,
                duration_ms=1234,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            row = table.get_row_at(0)
            # Duration >= 1000ms is formatted as seconds (e.g., "1.2s")
            assert str(row[5]) == "1.2s"

    @pytest.mark.asyncio
    async def test_missing_duration_shows_dash(self) -> None:
        """Test that missing duration shows dash."""
        from textual.app import App

        now = datetime.now(UTC)
        tasks = [
            Task(
                id="task-1",
                name="pending_task",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            row = table.get_row_at(0)
            # Now returns Text object
            assert str(row[5]) == "-"

    @pytest.mark.asyncio
    async def test_completed_tasks_sorted_to_bottom(self) -> None:
        """Test that completed and cancelled tasks are sorted to bottom."""
        from textual.app import App

        now = datetime.now(UTC)
        tasks = [
            Task(
                id="task-1",
                name="completed_task",
                queue="default",
                status=TaskStatus.COMPLETED,
                enqueued_at=now,
            ),
            Task(
                id="task-2",
                name="pending_task",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
            Task(
                id="task-3",
                name="cancelled_task",
                queue="default",
                status=TaskStatus.CANCELLED,
                enqueued_at=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            # Check that pending task is first
            first_row = table.get_row_at(0)
            assert str(first_row[1]) == "pending_task"

    @pytest.mark.asyncio
    async def test_row_selection_posts_message(self) -> None:
        """Test that selecting a row posts TaskSelected message."""
        from textual.app import App

        now = datetime.now(UTC)
        task_id = "task-1234-5678-9abc-def0"
        tasks = [
            Task(
                id=task_id,
                name="test_task",
                queue="default",
                status=TaskStatus.PENDING,
                enqueued_at=now,
            ),
        ]

        messages: list[TaskTable.TaskSelected] = []

        class TestApp(App[None]):
            def compose(self):
                yield TaskTable(id="test-table")

            def on_task_table_task_selected(self, event: TaskTable.TaskSelected) -> None:
                messages.append(event)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", TaskTable)
            table.update_tasks(tasks)
            await pilot.pause()

            # Focus the table and select the row
            table.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert len(messages) == 1
            assert messages[0].task_id == task_id
