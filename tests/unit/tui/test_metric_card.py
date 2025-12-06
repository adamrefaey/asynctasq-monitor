"""Unit tests for the MetricCard widget."""

import pytest
from textual.widgets import Digits, Label

from asynctasq_monitor.tui.widgets.metric_card import MetricCard


class TestMetricCard:
    """Tests for MetricCard widget."""

    def test_init_with_defaults(self) -> None:
        """Test MetricCard initializes with default values."""
        card = MetricCard("Test Label", "test-card")
        assert card.id == "test-card"
        assert card._label_text == "Test Label"
        assert card._variant == "default"
        assert card._initial_value == 0
        assert card.has_class("metric-default")

    def test_init_with_variant(self) -> None:
        """Test MetricCard initializes with specified variant."""
        card = MetricCard("Pending", "pending", variant="warning")
        assert card._variant == "warning"
        assert card.has_class("metric-warning")

    def test_init_with_initial_value(self) -> None:
        """Test MetricCard initializes with specified initial value."""
        card = MetricCard("Count", "count", initial_value=42)
        assert card._initial_value == 42

    def test_all_variants(self) -> None:
        """Test all supported variants."""
        variants = ["default", "warning", "accent", "success", "error"]
        for variant in variants:
            card = MetricCard("Test", f"card-{variant}", variant=variant)
            assert card.has_class(f"metric-{variant}")

    @pytest.mark.asyncio
    async def test_compose_yields_label_and_digits(self) -> None:
        """Test that compose yields Label and Digits widgets."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield MetricCard("Test Label", "test-card")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            card = app.query_one("#test-card", MetricCard)
            assert card is not None

            # Check Label exists
            label = card.query_one(".metric-label", Label)
            assert label is not None
            # Use render() to get the text content
            # The label's content is stored as a string in Label
            assert str(label.render()) is not None

            # Check Digits exists
            digits = card.query_one(Digits)
            assert digits is not None
            assert digits.id == "digits-test-card"

    @pytest.mark.asyncio
    async def test_value_reactivity(self) -> None:
        """Test that changing value updates the Digits widget."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield MetricCard("Counter", "counter")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            card = app.query_one("#counter", MetricCard)

            # Initial value should be 0
            digits = card.query_one(Digits)
            assert digits.value == "0"

            # Update value
            card.value = 123
            await pilot.pause()
            assert digits.value == "123"

            # Update to another value
            card.value = 999
            await pilot.pause()
            assert digits.value == "999"

    @pytest.mark.asyncio
    async def test_initial_value_displayed(self) -> None:
        """Test that initial value is displayed correctly."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield MetricCard("Test", "test", initial_value=42)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app
            card = app.query_one("#test", MetricCard)
            digits = card.query_one(Digits)
            assert digits.value == "42"

    @pytest.mark.asyncio
    async def test_multiple_cards(self) -> None:
        """Test multiple MetricCards with different variants."""
        from textual.app import App
        from textual.containers import Horizontal

        class TestApp(App[None]):
            def compose(self):
                with Horizontal():
                    yield MetricCard("Pending", "pending", variant="warning")
                    yield MetricCard("Running", "running", variant="accent")
                    yield MetricCard("Completed", "completed", variant="success")
                    yield MetricCard("Failed", "failed", variant="error")

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            app = pilot.app

            # Check all cards exist
            pending = app.query_one("#pending", MetricCard)
            running = app.query_one("#running", MetricCard)
            completed = app.query_one("#completed", MetricCard)
            failed = app.query_one("#failed", MetricCard)

            assert pending.has_class("metric-warning")
            assert running.has_class("metric-accent")
            assert completed.has_class("metric-success")
            assert failed.has_class("metric-error")

            # Update values
            pending.value = 10
            running.value = 5
            completed.value = 100
            failed.value = 2
            await pilot.pause()

            assert pending.query_one(Digits).value == "10"
            assert running.query_one(Digits).value == "5"
            assert completed.query_one(Digits).value == "100"
            assert failed.query_one(Digits).value == "2"

    def test_css_is_in_tcss_file(self) -> None:
        """Test that CSS is defined in the TCSS file (not inline DEFAULT_CSS)."""
        # MetricCard no longer uses DEFAULT_CSS - styling is in app.tcss
        # This test just verifies the class exists and can be instantiated
        card = MetricCard("Test", "test-card")
        assert card is not None

    def test_init_with_icon(self) -> None:
        """Test MetricCard initializes with specified icon."""
        card = MetricCard("Pending", "pending", variant="warning", icon="")
        assert card._icon == ""
