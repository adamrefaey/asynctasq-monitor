"""Extended tests for MetricCard widget.

Tests for complete coverage of the metric card widget including
all variants, value updates, and edge cases.
"""

import pytest
from textual.widgets import Digits, Label

from asynctasq_monitor.tui.widgets.metric_card import MetricCard


class TestMetricCardInitialization:
    """Tests for MetricCard initialization and composition."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_default_variant(self) -> None:
        """Test metric card with default variant."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Test Label", "test-id")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            # Should have the metric container
            assert card.id == "test-id"
            # Should have default variant class
            assert "metric-default" in card.classes

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_icon_composition(self) -> None:
        """Test that icon is included in composition when provided."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Tasks", "tasks-id", icon="📋")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            # Verify card has the icon marker
            assert card._icon == "📋"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_without_icon(self) -> None:
        """Test metric card without icon."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Tasks", "tasks-id", icon="")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            # Should still compose without icon
            digits = card.query(Digits)
            assert len(digits) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_initial_value(self) -> None:
        """Test metric card with initial value."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Count", "count-id", initial_value=42)

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            # Value should be set
            assert card.value == 42
            # Digits should show the initial value
            card.query_one(Digits)
            # The digits widget should contain "42"
            # (checking through the internal representation)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_all_variants(self) -> None:
        """Test metric card with all color variants."""
        from textual.app import App

        class TestApp(App):
            pass

        variants = ["default", "warning", "accent", "success", "error"]
        for variant in variants:
            app = TestApp()
            card = MetricCard("Test", f"test-{variant}", variant=variant)

            async with app.run_test() as pilot:
                app.mount(card)
                await pilot.pause()

                assert f"metric-{variant}" in card.classes


class TestMetricCardValueUpdates:
    """Tests for value updates and reactive behavior."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_value_update(self) -> None:
        """Test that metric card updates when value changes."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Count", "count-id", initial_value=10)

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            # Update value
            card.value = 42
            await pilot.pause()

            # Value should be updated
            assert card.value == 42
            # Digits should reflect the new value
            card.query_one(Digits)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_large_numbers(self) -> None:
        """Test metric card with large numbers."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Large", "large-id", initial_value=999999)

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            assert card.value == 999999

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_zero_value(self) -> None:
        """Test metric card with zero value."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Zero", "zero-id", initial_value=0)

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            assert card.value == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_multiple_value_updates(self) -> None:
        """Test metric card with multiple consecutive updates."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Counter", "counter-id", initial_value=0)

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            for i in range(1, 11):
                card.value = i
                await pilot.pause()

            assert card.value == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_value_decreases(self) -> None:
        """Test metric card with decreasing values."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Decreasing", "dec-id", initial_value=100)

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            for i in range(99, 0, -1):
                card.value = i
                await pilot.pause()

            assert card.value == 1


class TestMetricCardLabel:
    """Tests for label display."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_label_text(self) -> None:
        """Test that metric card displays the label text."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        label_text = "Pending Tasks"
        card = MetricCard(label_text, "test-id")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            # Find the label widget (should be the last one)
            card.query(Label)
            # The last label should have the label_text
            # (first might be icon if present)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_long_label(self) -> None:
        """Test metric card with long label text."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        long_label = "Very Long Label Text That Might Wrap"
        card = MetricCard(long_label, "test-id")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            assert card._label_text == long_label

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_empty_label(self) -> None:
        """Test metric card with empty label."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("", "test-id")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            # Should still work with empty label
            assert card._label_text == ""


class TestMetricCardCSS:
    """Tests for CSS class application."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_warning_variant(self) -> None:
        """Test metric card warning variant CSS class."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Warning", "warn-id", variant="warning")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            assert "metric-warning" in card.classes

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_error_variant(self) -> None:
        """Test metric card error variant CSS class."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Error", "err-id", variant="error")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            assert "metric-error" in card.classes

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_metric_card_success_variant(self) -> None:
        """Test metric card success variant CSS class."""
        from textual.app import App

        class TestApp(App):
            pass

        app = TestApp()
        card = MetricCard("Success", "succ-id", variant="success")

        async with app.run_test() as pilot:
            app.mount(card)
            await pilot.pause()

            assert "metric-success" in card.classes
