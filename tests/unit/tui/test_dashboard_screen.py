"""Unit tests for the DashboardScreen."""

import pytest
from textual.widgets import Sparkline, Static

from asynctasq_monitor.tui.screens.dashboard import DashboardScreen
from asynctasq_monitor.tui.widgets.metric_card import MetricCard


class TestDashboardScreen:
    """Tests for DashboardScreen."""

    def test_init(self) -> None:
        """Test DashboardScreen initializes with default values."""
        screen = DashboardScreen()
        assert screen.pending_count == 0
        assert screen.running_count == 0
        assert screen.completed_count == 0
        assert screen.failed_count == 0
        assert screen.throughput_data == []

    @pytest.mark.asyncio
    async def test_compose_yields_expected_widgets(self) -> None:
        """Test that compose yields all expected widgets."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app

            # Check DashboardScreen exists
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)
            assert dashboard is not None

            # Check section titles
            labels = list(dashboard.query(".section-title"))
            assert len(labels) == 3
            # Just verify the labels exist - content testing done elsewhere

    @pytest.mark.asyncio
    async def test_metric_cards_exist(self) -> None:
        """Test that all four metric cards are created."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            # Check all metric cards exist
            pending = dashboard.query_one("#pending", MetricCard)
            running = dashboard.query_one("#running", MetricCard)
            completed = dashboard.query_one("#completed", MetricCard)
            failed = dashboard.query_one("#failed", MetricCard)

            assert pending is not None
            assert running is not None
            assert completed is not None
            assert failed is not None

            # Check variants
            assert pending.has_class("metric-warning")
            assert running.has_class("metric-accent")
            assert completed.has_class("metric-success")
            assert failed.has_class("metric-error")

    @pytest.mark.asyncio
    async def test_sparkline_exists(self) -> None:
        """Test that throughput sparkline is created."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            sparkline = dashboard.query_one("#throughput-sparkline", Sparkline)
            assert sparkline is not None
            assert sparkline.data == []

    @pytest.mark.asyncio
    async def test_recent_activity_exists(self) -> None:
        """Test that recent activity section is created."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            activity = dashboard.query_one("#recent-activity", Static)
            assert activity is not None
            # Widget exists and is a Static

    @pytest.mark.asyncio
    async def test_update_metrics(self) -> None:
        """Test updating all metrics at once."""
        from textual.app import App
        from textual.widgets import Digits

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            # Update metrics
            dashboard.update_metrics(
                pending=10,
                running=5,
                completed=100,
                failed=2,
            )
            await pilot.pause()

            # Check reactive values updated
            assert dashboard.pending_count == 10
            assert dashboard.running_count == 5
            assert dashboard.completed_count == 100
            assert dashboard.failed_count == 2

            # Check Digits widgets updated
            pending_digits = dashboard.query_one("#pending", MetricCard).query_one(Digits)
            running_digits = dashboard.query_one("#running", MetricCard).query_one(Digits)
            completed_digits = dashboard.query_one("#completed", MetricCard).query_one(Digits)
            failed_digits = dashboard.query_one("#failed", MetricCard).query_one(Digits)

            assert pending_digits.value == "10"
            assert running_digits.value == "5"
            assert completed_digits.value == "100"
            assert failed_digits.value == "2"

    @pytest.mark.asyncio
    async def test_add_throughput_sample(self) -> None:
        """Test adding throughput samples."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            # Add samples
            dashboard.add_throughput_sample(10.5)
            dashboard.add_throughput_sample(15.2)
            dashboard.add_throughput_sample(12.0)
            await pilot.pause()

            assert len(dashboard.throughput_data) == 3
            assert dashboard.throughput_data == [10.5, 15.2, 12.0]

    @pytest.mark.asyncio
    async def test_throughput_sample_limit(self) -> None:
        """Test that throughput samples are limited to 60."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            # Add more than 60 samples
            for i in range(70):
                dashboard.add_throughput_sample(float(i))

            assert len(dashboard.throughput_data) == 60
            # Should keep the last 60 samples (10-69)
            assert dashboard.throughput_data[0] == 10.0
            assert dashboard.throughput_data[-1] == 69.0

    @pytest.mark.asyncio
    async def test_update_activity(self) -> None:
        """Test updating the activity text."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            # Update activity
            dashboard.update_activity("Task 'process_data' completed successfully")
            await pilot.pause()

            activity = dashboard.query_one("#recent-activity", Static)
            # Verify the widget was updated (method was called without exception)
            assert activity is not None

    @pytest.mark.asyncio
    async def test_pending_count_reactivity(self) -> None:
        """Test pending count reactivity updates metric card."""
        from textual.app import App
        from textual.widgets import Digits

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            dashboard.pending_count = 42
            await pilot.pause()

            pending = dashboard.query_one("#pending", MetricCard)
            assert pending.value == 42
            assert pending.query_one(Digits).value == "42"

    @pytest.mark.asyncio
    async def test_running_count_reactivity(self) -> None:
        """Test running count reactivity updates metric card."""
        from textual.app import App
        from textual.widgets import Digits

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            dashboard.running_count = 5
            await pilot.pause()

            running = dashboard.query_one("#running", MetricCard)
            assert running.value == 5
            assert running.query_one(Digits).value == "5"

    @pytest.mark.asyncio
    async def test_completed_count_reactivity(self) -> None:
        """Test completed count reactivity updates metric card."""
        from textual.app import App
        from textual.widgets import Digits

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            dashboard.completed_count = 1000
            await pilot.pause()

            completed = dashboard.query_one("#completed", MetricCard)
            assert completed.value == 1000
            assert completed.query_one(Digits).value == "1000"

    @pytest.mark.asyncio
    async def test_failed_count_reactivity(self) -> None:
        """Test failed count reactivity updates metric card."""
        from textual.app import App
        from textual.widgets import Digits

        class TestApp(App[None]):
            def compose(self):
                yield DashboardScreen(id="dashboard-screen")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            dashboard = app.query_one("#dashboard-screen", DashboardScreen)

            dashboard.failed_count = 3
            await pilot.pause()

            failed = dashboard.query_one("#failed", MetricCard)
            assert failed.value == 3
            assert failed.query_one(Digits).value == "3"

    def test_default_css_exists(self) -> None:
        """Test that DEFAULT_CSS is defined."""
        assert DashboardScreen.DEFAULT_CSS is not None
        assert "DashboardScreen" in DashboardScreen.DEFAULT_CSS
        assert "#metrics-row" in DashboardScreen.DEFAULT_CSS
        assert ".section-title" in DashboardScreen.DEFAULT_CSS
        assert "#throughput-container" in DashboardScreen.DEFAULT_CSS
        assert "#recent-activity" in DashboardScreen.DEFAULT_CSS
