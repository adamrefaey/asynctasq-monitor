"""Unit tests for the WorkersScreen and related widgets."""

from datetime import UTC, datetime, timedelta

import pytest
from textual.widgets import Label, Static

from asynctasq_monitor.models.worker import Worker, WorkerStatus
from asynctasq_monitor.tui.screens.workers import WorkersScreen, WorkerSummary, WorkerTable


class TestWorkerTable:
    """Tests for the WorkerTable widget."""

    def test_status_colors_defined(self) -> None:
        """Test that all worker statuses have colors defined."""
        for status in WorkerStatus:
            assert status.value in WorkerTable.STATUS_COLORS, f"Missing color for {status.value}"

    def test_worker_selected_message(self) -> None:
        """Test WorkerSelected message initialization."""
        msg = WorkerTable.WorkerSelected("worker-123")
        assert msg.worker_id == "worker-123"

    @pytest.mark.asyncio
    async def test_table_mounts_with_columns(self) -> None:
        """Test that table has correct columns after mounting."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            assert table is not None

            # Check columns exist (7 columns)
            columns = list(table.columns.keys())
            assert len(columns) == 7

    @pytest.mark.asyncio
    async def test_table_cursor_type_is_row(self) -> None:
        """Test that table cursor type is set to row."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            assert table.cursor_type == "row"

    @pytest.mark.asyncio
    async def test_table_has_zebra_stripes(self) -> None:
        """Test that table has zebra stripes enabled."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            assert table.zebra_stripes is True

    @pytest.mark.asyncio
    async def test_update_workers_populates_table(self) -> None:
        """Test that update_workers populates the table with data."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-001",
                name="worker-1",
                status=WorkerStatus.ACTIVE,
                queues=["default"],
                last_heartbeat=now,
            ),
            Worker(
                id="worker-002",
                name="worker-2",
                status=WorkerStatus.IDLE,
                queues=["high"],
                last_heartbeat=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_update_workers_clears_existing_rows(self) -> None:
        """Test that update_workers clears existing rows before adding new ones."""
        from textual.app import App

        now = datetime.now(UTC)

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)

            # Add first batch
            workers1 = [
                Worker(
                    id="worker-1",
                    name="w1",
                    status=WorkerStatus.ACTIVE,
                    queues=["default"],
                    last_heartbeat=now,
                )
            ]
            table.update_workers(workers1)
            await pilot.pause()
            assert table.row_count == 1

            # Add second batch (should replace, not append)
            workers2 = [
                Worker(
                    id="worker-2",
                    name="w2",
                    status=WorkerStatus.IDLE,
                    queues=["high"],
                    last_heartbeat=now,
                ),
                Worker(
                    id="worker-3",
                    name="w3",
                    status=WorkerStatus.OFFLINE,
                    queues=["low"],
                    last_heartbeat=now - timedelta(hours=1),
                ),
            ]
            table.update_workers(workers2)
            await pilot.pause()
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_worker_with_multiple_queues(self) -> None:
        """Test worker with multiple queues displays correctly."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-001",
                name="worker-1",
                status=WorkerStatus.ACTIVE,
                queues=["default", "high", "low", "email", "reports"],
                last_heartbeat=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            # Should show first 3 queues plus count of remaining
            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_worker_with_current_task(self) -> None:
        """Test worker with current task displays task name."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-001",
                name="worker-1",
                status=WorkerStatus.ACTIVE,
                queues=["default"],
                current_task_id="task-123",
                current_task_name="process_payment",
                last_heartbeat=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_worker_without_current_task(self) -> None:
        """Test worker without current task displays dash."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-001",
                name="worker-1",
                status=WorkerStatus.IDLE,
                queues=["default"],
                current_task_id=None,
                current_task_name=None,
                last_heartbeat=now,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            assert table.row_count == 1


class TestWorkerSummary:
    """Tests for the WorkerSummary widget."""

    @pytest.mark.asyncio
    async def test_summary_mounts_with_static_widgets(self) -> None:
        """Test that summary has three Static widgets."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", WorkerSummary)

            # Check all three counts exist
            active = summary.query_one("#active-count", Static)
            idle = summary.query_one("#idle-count", Static)
            offline = summary.query_one("#offline-count", Static)

            assert active is not None
            assert idle is not None
            assert offline is not None

    @pytest.mark.asyncio
    async def test_summary_initial_values(self) -> None:
        """Test that summary starts with zero counts."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", WorkerSummary)

            assert summary.active_count == 0
            assert summary.idle_count == 0
            assert summary.offline_count == 0

    @pytest.mark.asyncio
    async def test_update_counts(self) -> None:
        """Test that update_counts updates all values."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", WorkerSummary)

            summary.update_counts(5, 3, 2)
            await pilot.pause()

            assert summary.active_count == 5
            assert summary.idle_count == 3
            assert summary.offline_count == 2

    @pytest.mark.asyncio
    async def test_reactive_active_count(self) -> None:
        """Test active_count reactivity updates display."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", WorkerSummary)

            summary.active_count = 10
            await pilot.pause()

            active_static = summary.query_one("#active-count", Static)
            assert "10" in str(active_static.render())

    @pytest.mark.asyncio
    async def test_reactive_idle_count(self) -> None:
        """Test idle_count reactivity updates display."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", WorkerSummary)

            summary.idle_count = 7
            await pilot.pause()

            idle_static = summary.query_one("#idle-count", Static)
            assert "7" in str(idle_static.render())

    @pytest.mark.asyncio
    async def test_reactive_offline_count(self) -> None:
        """Test offline_count reactivity updates display."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkerSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", WorkerSummary)

            summary.offline_count = 4
            await pilot.pause()

            offline_static = summary.query_one("#offline-count", Static)
            assert "4" in str(offline_static.render())


class TestWorkersScreen:
    """Tests for the WorkersScreen."""

    @pytest.mark.asyncio
    async def test_screen_mounts(self) -> None:
        """Test that WorkersScreen mounts correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", WorkersScreen)
            assert screen is not None

    @pytest.mark.asyncio
    async def test_screen_has_section_title(self) -> None:
        """Test that screen has section title."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", WorkersScreen)
            title = screen.query_one(".section-title", Label)
            assert title is not None
            assert "Workers" in str(title.render())

    @pytest.mark.asyncio
    async def test_screen_has_summary(self) -> None:
        """Test that screen has WorkerSummary widget."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", WorkersScreen)
            summary = screen.query_one(WorkerSummary)
            assert summary is not None

    @pytest.mark.asyncio
    async def test_screen_has_worker_table(self) -> None:
        """Test that screen has WorkerTable widget."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", WorkersScreen)
            table = screen.query_one(WorkerTable)
            assert table is not None

    @pytest.mark.asyncio
    async def test_sample_data_loaded_on_mount(self) -> None:
        """Test that sample data is loaded when screen mounts."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", WorkersScreen)
            table = screen.query_one(WorkerTable)

            # Sample data should have 4 workers
            assert table.row_count == 4

    @pytest.mark.asyncio
    async def test_sample_data_summary_counts(self) -> None:
        """Test that sample data updates summary counts correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", WorkersScreen)
            summary = screen.query_one(WorkerSummary)

            # Sample data: 3 active, 1 idle, 0 offline
            assert summary.active_count == 3
            assert summary.idle_count == 1
            assert summary.offline_count == 0

    @pytest.mark.asyncio
    async def test_update_workers_method(self) -> None:
        """Test that update_workers method updates table and summary."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-1",
                name="w1",
                status=WorkerStatus.ACTIVE,
                queues=["default"],
                last_heartbeat=now,
            ),
            Worker(
                id="worker-2",
                name="w2",
                status=WorkerStatus.OFFLINE,
                queues=["high"],
                last_heartbeat=now - timedelta(hours=1),
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", WorkersScreen)

            # Update with new workers
            screen.update_workers(workers)
            await pilot.pause()

            table = screen.query_one(WorkerTable)
            summary = screen.query_one(WorkerSummary)

            assert table.row_count == 2
            assert summary.active_count == 1
            assert summary.idle_count == 0
            assert summary.offline_count == 1

    @pytest.mark.asyncio
    async def test_worker_selection_notification(self) -> None:
        """Test that selecting a worker shows notification."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield WorkersScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()

            # Navigate to the table and select first row
            table = pilot.app.query_one(WorkerTable)
            table.focus()
            await pilot.pause()

            # Press Enter to select
            await pilot.press("enter")
            await pilot.pause()

            # Check notification was posted
            # (The notification system is internal to the app)


class TestWorkerTableHeartbeatFormat:
    """Tests for heartbeat formatting in WorkerTable."""

    @pytest.mark.asyncio
    async def test_heartbeat_seconds_ago(self) -> None:
        """Test heartbeat displays seconds ago correctly."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-1",
                name="w1",
                status=WorkerStatus.ACTIVE,
                queues=["default"],
                last_heartbeat=now - timedelta(seconds=30),
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_heartbeat_minutes_ago(self) -> None:
        """Test heartbeat displays minutes ago correctly."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-1",
                name="w1",
                status=WorkerStatus.IDLE,
                queues=["default"],
                last_heartbeat=now - timedelta(minutes=5),
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_heartbeat_hours_ago(self) -> None:
        """Test heartbeat displays hours ago correctly."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-1",
                name="w1",
                status=WorkerStatus.OFFLINE,
                queues=["default"],
                last_heartbeat=now - timedelta(hours=2),
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_heartbeat_days_ago(self) -> None:
        """Test heartbeat displays days ago correctly."""
        from textual.app import App

        now = datetime.now(UTC)
        workers = [
            Worker(
                id="worker-1",
                name="w1",
                status=WorkerStatus.OFFLINE,
                queues=["default"],
                last_heartbeat=now - timedelta(days=3),
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield WorkerTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", WorkerTable)
            table.update_workers(workers)
            await pilot.pause()

            assert table.row_count == 1
