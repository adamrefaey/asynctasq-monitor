"""Unit tests for the LoadBar widget."""

import pytest
from textual.widgets import Label, ProgressBar

from asynctasq_monitor.tui.widgets.load_bar import LoadBar


class TestLoadBar:
    """Tests for the LoadBar widget."""

    def test_init_with_defaults(self) -> None:
        """Test LoadBar initializes with default values."""
        load_bar = LoadBar("CPU")
        assert load_bar._label_text == "CPU"
        assert load_bar._max_val == 100
        assert load_bar._initial_value == 0

    def test_init_with_custom_values(self) -> None:
        """Test LoadBar initializes with custom values."""
        load_bar = LoadBar("Memory", max_val=1024, initial_value=512, bar_id="mem-bar")
        assert load_bar.id == "mem-bar"
        assert load_bar._label_text == "Memory"
        assert load_bar._max_val == 1024
        assert load_bar._initial_value == 512

    def test_threshold_constants(self) -> None:
        """Test threshold constants are defined correctly."""
        assert LoadBar.THRESHOLD_LOW == 50
        assert LoadBar.THRESHOLD_HIGH == 80

    @pytest.mark.asyncio
    async def test_percentage_property(self) -> None:
        """Test percentage property calculates correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)

            # Initial value should be 0%
            assert load_bar.percentage == 0.0

            # Update to 50
            load_bar.value = 50
            await pilot.pause()
            assert load_bar.percentage == 50.0

    @pytest.mark.asyncio
    async def test_percentage_property_with_max_val_zero(self) -> None:
        """Test percentage property handles zero max_val."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", max_val=0, bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)
            # Should return 0.0 when max_val is 0
            assert load_bar.percentage == 0.0

    @pytest.mark.asyncio
    async def test_compose_yields_label_and_progress_bar(self) -> None:
        """Test that compose yields Label and ProgressBar widgets."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            load_bar = app.query_one("#cpu-bar", LoadBar)
            assert load_bar is not None

            # Check Label exists
            label = load_bar.query_one(".load-label", Label)
            assert label is not None
            assert "CPU:" in str(label.render())

            # Check ProgressBar exists
            progress = load_bar.query_one(ProgressBar)
            assert progress is not None

    @pytest.mark.asyncio
    async def test_initial_value_displayed(self) -> None:
        """Test that initial value is displayed correctly on mount."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("Memory", initial_value=75, bar_id="mem-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#mem-bar", LoadBar)
            assert load_bar.value == 75

    @pytest.mark.asyncio
    async def test_value_reactivity(self) -> None:
        """Test that changing value updates the widget."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)

            # Initial value should be 0
            assert load_bar.value == 0

            # Update value
            load_bar.value = 50
            await pilot.pause()
            assert load_bar.value == 50

            # Update to another value
            load_bar.value = 95
            await pilot.pause()
            assert load_bar.value == 95

    @pytest.mark.asyncio
    async def test_load_class_low(self) -> None:
        """Test load-low class applied for values below threshold."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", initial_value=30, bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)
            assert load_bar.has_class("load-low")
            assert not load_bar.has_class("load-medium")
            assert not load_bar.has_class("load-high")

    @pytest.mark.asyncio
    async def test_load_class_medium(self) -> None:
        """Test load-medium class applied for values at/above low threshold."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", initial_value=60, bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)
            assert not load_bar.has_class("load-low")
            assert load_bar.has_class("load-medium")
            assert not load_bar.has_class("load-high")

    @pytest.mark.asyncio
    async def test_load_class_high(self) -> None:
        """Test load-high class applied for values at/above high threshold."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", initial_value=85, bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)
            assert not load_bar.has_class("load-low")
            assert not load_bar.has_class("load-medium")
            assert load_bar.has_class("load-high")

    @pytest.mark.asyncio
    async def test_load_class_transitions(self) -> None:
        """Test that load class changes correctly when value changes."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)

            # Start at 0 - should be low
            assert load_bar.has_class("load-low")

            # Increase to medium
            load_bar.value = 55
            await pilot.pause()
            assert load_bar.has_class("load-medium")
            assert not load_bar.has_class("load-low")

            # Increase to high
            load_bar.value = 90
            await pilot.pause()
            assert load_bar.has_class("load-high")
            assert not load_bar.has_class("load-medium")

            # Decrease back to low
            load_bar.value = 25
            await pilot.pause()
            assert load_bar.has_class("load-low")
            assert not load_bar.has_class("load-high")

    @pytest.mark.asyncio
    async def test_boundary_values(self) -> None:
        """Test load class at exact boundary values."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)

            # Exactly at low threshold - should be medium
            load_bar.value = 50
            await pilot.pause()
            assert load_bar.has_class("load-medium")

            # Just below low threshold - should be low
            load_bar.value = 49
            await pilot.pause()
            assert load_bar.has_class("load-low")

            # Exactly at high threshold - should be high
            load_bar.value = 80
            await pilot.pause()
            assert load_bar.has_class("load-high")

            # Just below high threshold - should be medium
            load_bar.value = 79
            await pilot.pause()
            assert load_bar.has_class("load-medium")

    @pytest.mark.asyncio
    async def test_custom_max_val_percentage(self) -> None:
        """Test that percentage is calculated correctly with custom max_val."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("Memory", max_val=1024, bar_id="mem-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#mem-bar", LoadBar)

            # 512 out of 1024 = 50%
            load_bar.value = 512
            await pilot.pause()
            assert load_bar.percentage == 50.0
            assert load_bar.has_class("load-medium")

            # 820 out of 1024 > 80% (should be high)
            load_bar.value = 820
            await pilot.pause()
            assert load_bar.percentage == pytest.approx(80.078, rel=0.01)
            assert load_bar.has_class("load-high")

    @pytest.mark.asyncio
    async def test_progress_bar_configuration(self) -> None:
        """Test that ProgressBar is configured correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield LoadBar("CPU", max_val=100, bar_id="cpu-bar")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            load_bar = pilot.app.query_one("#cpu-bar", LoadBar)
            progress = load_bar.query_one(ProgressBar)

            # Check show_percentage is True
            assert progress.show_percentage is True
            # Check show_eta is False
            assert progress.show_eta is False
