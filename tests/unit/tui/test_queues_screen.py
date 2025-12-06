"""Unit tests for the QueuesScreen and related widgets."""

import pytest
from textual.widgets import Label, Static

from asynctasq_monitor.models.queue import Queue, QueueStatus
from asynctasq_monitor.tui.screens.queues import QueuesScreen, QueueSummary, QueueTable


class TestQueueTable:
    """Tests for the QueueTable widget."""

    def test_health_colors_defined(self) -> None:
        """Test that all health statuses have colors defined."""
        expected_statuses = ["ok", "warn", "crit", "paused"]
        for status in expected_statuses:
            assert status in QueueTable.HEALTH_COLORS, f"Missing color for {status}"

    def test_queue_selected_message(self) -> None:
        """Test QueueSelected message initialization."""
        msg = QueueTable.QueueSelected("default")
        assert msg.queue_name == "default"

    @pytest.mark.asyncio
    async def test_table_mounts_with_columns(self) -> None:
        """Test that table has correct columns after mounting."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
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
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            assert table.cursor_type == "row"

    @pytest.mark.asyncio
    async def test_table_has_zebra_stripes(self) -> None:
        """Test that table has zebra stripes enabled."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            assert table.zebra_stripes is True

    @pytest.mark.asyncio
    async def test_update_queues_populates_table(self) -> None:
        """Test that update_queues populates the table with data."""
        from textual.app import App

        queues = [
            Queue(
                name="default",
                status=QueueStatus.ACTIVE,
                depth=42,
                processing=3,
                workers_assigned=2,
            ),
            Queue(
                name="high",
                status=QueueStatus.ACTIVE,
                depth=8,
                processing=1,
                workers_assigned=1,
            ),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            table.update_queues(queues)
            await pilot.pause()

            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_update_queues_clears_existing_rows(self) -> None:
        """Test that update_queues clears existing rows before adding new ones."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)

            # Add first batch
            queues1 = [
                Queue(
                    name="default",
                    status=QueueStatus.ACTIVE,
                    depth=10,
                    processing=1,
                )
            ]
            table.update_queues(queues1)
            await pilot.pause()
            assert table.row_count == 1

            # Add second batch (should replace, not append)
            queues2 = [
                Queue(
                    name="high",
                    status=QueueStatus.ACTIVE,
                    depth=5,
                    processing=2,
                ),
                Queue(
                    name="low",
                    status=QueueStatus.PAUSED,
                    depth=0,
                    processing=0,
                ),
            ]
            table.update_queues(queues2)
            await pilot.pause()
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_health_status_ok(self) -> None:
        """Test health status is OK for low depth queues."""
        from textual.app import App

        queues = [
            Queue(
                name="default",
                status=QueueStatus.ACTIVE,
                depth=50,  # Below 100 threshold
                processing=1,
            )
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            table.update_queues(queues)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_health_status_warn(self) -> None:
        """Test health status is WARN for queues with depth >= 100."""
        from textual.app import App

        queues = [
            Queue(
                name="default",
                status=QueueStatus.ACTIVE,
                depth=150,  # Between 100 and 500
                processing=1,
            )
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            table.update_queues(queues)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_health_status_crit(self) -> None:
        """Test health status is CRIT for queues with depth >= 500."""
        from textual.app import App

        queues = [
            Queue(
                name="default",
                status=QueueStatus.ACTIVE,
                depth=600,  # Above 500 threshold
                processing=1,
            )
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            table.update_queues(queues)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_health_status_paused(self) -> None:
        """Test health status shows paused for paused queues."""
        from textual.app import App

        queues = [
            Queue(
                name="email",
                status=QueueStatus.PAUSED,
                depth=0,
                processing=0,
            )
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            table.update_queues(queues)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_queue_with_throughput(self) -> None:
        """Test queue with throughput displays rate correctly."""
        from textual.app import App

        queues = [
            Queue(
                name="default",
                status=QueueStatus.ACTIVE,
                depth=42,
                processing=3,
                throughput_per_minute=45.2,
            )
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            table.update_queues(queues)
            await pilot.pause()

            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_queue_without_throughput(self) -> None:
        """Test queue without throughput displays zero rate."""
        from textual.app import App

        queues = [
            Queue(
                name="email",
                status=QueueStatus.PAUSED,
                depth=0,
                processing=0,
                throughput_per_minute=None,
            )
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueTable(id="test-table")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            table = pilot.app.query_one("#test-table", QueueTable)
            table.update_queues(queues)
            await pilot.pause()

            assert table.row_count == 1


class TestQueueSummary:
    """Tests for the QueueSummary widget."""

    @pytest.mark.asyncio
    async def test_summary_mounts_with_static_widgets(self) -> None:
        """Test that summary has three Static widgets."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", QueueSummary)

            # Check all three stats exist
            queue_count = summary.query_one("#queue-count", Static)
            pending_count = summary.query_one("#pending-count", Static)
            rate_display = summary.query_one("#rate-display", Static)

            assert queue_count is not None
            assert pending_count is not None
            assert rate_display is not None

    @pytest.mark.asyncio
    async def test_summary_initial_values(self) -> None:
        """Test that summary starts with zero values."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", QueueSummary)

            assert summary.total_queues == 0
            assert summary.total_pending == 0
            assert summary.total_rate == 0.0

    @pytest.mark.asyncio
    async def test_update_stats(self) -> None:
        """Test that update_stats calculates values from queue list."""
        from textual.app import App

        queues = [
            Queue(name="default", depth=42, processing=3, throughput_per_minute=45.0),
            Queue(name="high", depth=8, processing=1, throughput_per_minute=28.0),
            Queue(name="low", depth=12, processing=2, throughput_per_minute=None),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueueSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", QueueSummary)

            summary.update_stats(queues)
            await pilot.pause()

            assert summary.total_queues == 3
            assert summary.total_pending == 62  # 42 + 8 + 12
            assert summary.total_rate == 73.0  # 45 + 28 + 0

    @pytest.mark.asyncio
    async def test_reactive_total_queues(self) -> None:
        """Test total_queues reactivity updates display."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", QueueSummary)

            summary.total_queues = 5
            await pilot.pause()

            queue_static = summary.query_one("#queue-count", Static)
            assert "5" in str(queue_static.render())

    @pytest.mark.asyncio
    async def test_reactive_total_pending(self) -> None:
        """Test total_pending reactivity updates display."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", QueueSummary)

            summary.total_pending = 1234
            await pilot.pause()

            pending_static = summary.query_one("#pending-count", Static)
            # Should include formatted number with commas
            assert "1,234" in str(pending_static.render())

    @pytest.mark.asyncio
    async def test_reactive_total_rate(self) -> None:
        """Test total_rate reactivity updates display."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueueSummary(id="test-summary")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            summary = pilot.app.query_one("#test-summary", QueueSummary)

            summary.total_rate = 156.5
            await pilot.pause()

            rate_static = summary.query_one("#rate-display", Static)
            # Uses .0f formatting which truncates
            assert "156/m" in str(rate_static.render())


class TestQueuesScreen:
    """Tests for the QueuesScreen."""

    @pytest.mark.asyncio
    async def test_screen_mounts(self) -> None:
        """Test that QueuesScreen mounts correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)
            assert screen is not None

    @pytest.mark.asyncio
    async def test_screen_has_section_title(self) -> None:
        """Test that screen has section title."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)
            title = screen.query_one(".section-title", Label)
            assert title is not None
            assert "Queues" in str(title.render())

    @pytest.mark.asyncio
    async def test_screen_has_summary(self) -> None:
        """Test that screen has QueueSummary widget."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)
            summary = screen.query_one(QueueSummary)
            assert summary is not None

    @pytest.mark.asyncio
    async def test_screen_has_queue_table(self) -> None:
        """Test that screen has QueueTable widget."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)
            table = screen.query_one(QueueTable)
            assert table is not None

    @pytest.mark.asyncio
    async def test_sample_data_loaded_on_mount(self) -> None:
        """Test that sample data is loaded when screen mounts."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)
            table = screen.query_one(QueueTable)

            # Sample data should have 5 queues
            assert table.row_count == 5

    @pytest.mark.asyncio
    async def test_sample_data_summary_stats(self) -> None:
        """Test that sample data updates summary stats correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)
            summary = screen.query_one(QueueSummary)

            # Sample data has 5 queues
            assert summary.total_queues == 5
            # Sum of sample depths: 42 + 8 + 0 + 156 + 12 = 218
            assert summary.total_pending == 218

    @pytest.mark.asyncio
    async def test_update_queues_method(self) -> None:
        """Test that update_queues updates both table and summary."""
        from textual.app import App

        new_queues = [
            Queue(name="test1", depth=100, processing=5, throughput_per_minute=50.0),
            Queue(name="test2", depth=200, processing=10, throughput_per_minute=75.0),
        ]

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)

            screen.update_queues(new_queues)
            await pilot.pause()

            table = screen.query_one(QueueTable)
            summary = screen.query_one(QueueSummary)

            assert table.row_count == 2
            assert summary.total_queues == 2
            assert summary.total_pending == 300  # 100 + 200
            assert summary.total_rate == 125.0  # 50 + 75

    @pytest.mark.asyncio
    async def test_queue_selected_notification(self) -> None:
        """Test that selecting a queue shows notification."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)

            # Post a queue selected message
            screen.post_message(QueueTable.QueueSelected("default"))
            await pilot.pause()

            # Notification should be shown (we can't easily verify the notification
            # content in tests, but we can verify no exceptions occurred)

    @pytest.mark.asyncio
    async def test_reactive_queues_list(self) -> None:
        """Test that queues reactive list is properly initialized."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)

            # After mount, queues should be loaded with sample data
            assert len(screen.queues) == 5

    @pytest.mark.asyncio
    async def test_queue_table_columns(self) -> None:
        """Test that queue table has all expected columns."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield QueuesScreen(id="test-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            screen = pilot.app.query_one("#test-screen", QueuesScreen)
            table = screen.query_one(QueueTable)

            # Verify table has correct number of columns
            columns = list(table.columns.keys())
            assert len(columns) == 7  # Queue, Health, Pending, Processing, Rate, Workers, Oldest


class TestQueueTableHealthStatus:
    """Tests for the QueueTable health status logic."""

    def test_get_health_status_ok(self) -> None:
        """Test health status returns OK for low depth active queue."""
        table = QueueTable()
        queue = Queue(name="test", status=QueueStatus.ACTIVE, depth=50)
        status, color = table._get_health_status(queue)
        assert status == "● OK"
        assert color == "green"

    def test_get_health_status_warn(self) -> None:
        """Test health status returns WARN for medium depth queue."""
        table = QueueTable()
        queue = Queue(name="test", status=QueueStatus.ACTIVE, depth=150)
        status, color = table._get_health_status(queue)
        assert status == "⚠ Warn"
        assert color == "yellow"

    def test_get_health_status_crit(self) -> None:
        """Test health status returns CRIT for high depth queue."""
        table = QueueTable()
        queue = Queue(name="test", status=QueueStatus.ACTIVE, depth=600)
        status, color = table._get_health_status(queue)
        assert status == "⊗ Crit"
        assert color == "red"

    def test_get_health_status_paused(self) -> None:
        """Test health status returns Paused for paused queue."""
        table = QueueTable()
        queue = Queue(name="test", status=QueueStatus.PAUSED, depth=0)
        status, color = table._get_health_status(queue)
        assert status == "⏸ Paused"
        assert color == "cyan"

    def test_get_health_status_paused_overrides_depth(self) -> None:
        """Test that paused status overrides depth-based health."""
        table = QueueTable()
        # Even with high depth, paused should show paused status
        queue = Queue(name="test", status=QueueStatus.PAUSED, depth=1000)
        status, color = table._get_health_status(queue)
        assert status == "⏸ Paused"
        assert color == "cyan"


class TestQueueTableFormatRate:
    """Tests for the QueueTable rate formatting."""

    def test_format_rate_with_value(self) -> None:
        """Test rate formatting with throughput value."""
        table = QueueTable()
        queue = Queue(name="test", throughput_per_minute=45.7)
        rate = table._format_rate(queue)
        assert "46/m" in str(rate)  # Rounded

    def test_format_rate_zero(self) -> None:
        """Test rate formatting with zero throughput."""
        table = QueueTable()
        queue = Queue(name="test", throughput_per_minute=0.0)
        rate = table._format_rate(queue)
        assert "0/m" in str(rate)

    def test_format_rate_none(self) -> None:
        """Test rate formatting with no throughput data."""
        table = QueueTable()
        queue = Queue(name="test", throughput_per_minute=None)
        rate = table._format_rate(queue)
        assert "0/m" in str(rate)


class TestQueueTableFormatOldestTask:
    """Tests for the QueueTable oldest task formatting."""

    def test_format_oldest_empty_queue(self) -> None:
        """Test oldest task formatting for empty queue."""
        table = QueueTable()
        queue = Queue(name="test", depth=0)
        oldest = table._format_oldest_task(queue)
        assert oldest == "-"

    def test_format_oldest_with_tasks(self) -> None:
        """Test oldest task formatting for queue with tasks."""
        table = QueueTable()
        queue = Queue(name="test", depth=10)
        oldest = table._format_oldest_task(queue)
        # Should return placeholder for now
        assert oldest != "-"
