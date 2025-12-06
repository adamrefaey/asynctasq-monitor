"""Unit tests for the FilterBar widget."""

import pytest
from textual.widgets import Input, Select

from asynctasq_monitor.tui.widgets.filter_bar import FilterBar


class TestFilterBar:
    """Tests for the FilterBar widget."""

    def test_filter_changed_message(self) -> None:
        """Test FilterChanged message initialization."""
        msg = FilterBar.FilterChanged(
            search="test",
            status="running",
            queue="high",
        )
        assert msg.search == "test"
        assert msg.status == "running"
        assert msg.queue == "high"

    def test_init_with_defaults(self) -> None:
        """Test FilterBar initializes with empty lists by default."""
        bar = FilterBar()
        assert bar._statuses == []
        assert bar._queues == []

    def test_init_with_custom_values(self) -> None:
        """Test FilterBar initializes with provided values."""
        statuses = ["pending", "running"]
        queues = ["default", "high"]
        bar = FilterBar(statuses=statuses, queues=queues)
        assert bar._statuses == statuses
        assert bar._queues == queues

    @pytest.mark.asyncio
    async def test_compose_yields_input_and_selects(self) -> None:
        """Test that compose yields Input and Select widgets."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield FilterBar(
                    statuses=["pending", "running"],
                    queues=["default", "high"],
                    id="filter-bar",
                )

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            bar = pilot.app.query_one("#filter-bar", FilterBar)

            # Check widgets exist
            search_input = bar.query_one("#search-input", Input)
            assert search_input is not None
            assert search_input.placeholder == "Search by name or ID..."

            status_select = bar.query_one("#status-filter", Select)
            assert status_select is not None

            queue_select = bar.query_one("#queue-filter", Select)
            assert queue_select is not None

    @pytest.mark.asyncio
    async def test_status_select_has_all_status_option(self) -> None:
        """Test that status select includes 'All Status' option."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield FilterBar(
                    statuses=["pending", "running"],
                    id="filter-bar",
                )

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            bar = pilot.app.query_one("#filter-bar", FilterBar)
            status_select = bar.query_one("#status-filter", Select)
            assert status_select.value == "All Status"

    @pytest.mark.asyncio
    async def test_queue_select_has_all_queues_option(self) -> None:
        """Test that queue select includes 'All Queues' option."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield FilterBar(
                    queues=["default", "high"],
                    id="filter-bar",
                )

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            bar = pilot.app.query_one("#filter-bar", FilterBar)
            queue_select = bar.query_one("#queue-filter", Select)
            assert queue_select.value == "All Queues"

    @pytest.mark.asyncio
    async def test_input_change_emits_filter_changed(self) -> None:
        """Test that changing input emits FilterChanged message."""
        from textual.app import App

        messages: list[FilterBar.FilterChanged] = []

        class TestApp(App[None]):
            def compose(self):
                yield FilterBar(id="filter-bar")

            def on_filter_bar_filter_changed(self, event: FilterBar.FilterChanged) -> None:
                messages.append(event)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            bar = pilot.app.query_one("#filter-bar", FilterBar)
            search_input = bar.query_one("#search-input", Input)

            # Type in the search box
            search_input.focus()
            await pilot.pause()
            search_input.value = "test"
            await pilot.pause()

            # Should have received filter changed messages
            assert len(messages) > 0
            # Last message should have the search value
            assert messages[-1].search == "test"

    @pytest.mark.asyncio
    async def test_reset_filters(self) -> None:
        """Test that reset_filters clears all filter values."""
        from textual.app import App

        class TestApp(App[None]):
            def compose(self):
                yield FilterBar(
                    statuses=["pending"],
                    queues=["high"],
                    id="filter-bar",
                )

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            bar = pilot.app.query_one("#filter-bar", FilterBar)

            # Set some values
            search_input = bar.query_one("#search-input", Input)
            search_input.value = "test search"
            await pilot.pause()

            # Reset filters
            bar.reset_filters()
            await pilot.pause()

            # Check all values are reset
            assert bar.query_one("#search-input", Input).value == ""
            assert bar.query_one("#status-filter", Select).value == "All Status"
            assert bar.query_one("#queue-filter", Select).value == "All Queues"
