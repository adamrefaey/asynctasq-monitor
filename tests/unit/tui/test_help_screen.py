"""Tests for TUI help screen.

Tests for the help modal screen.
"""

import pytest

from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI
from asynctasq_monitor.tui.screens.help import KEYBINDINGS_TEXT, HelpScreen


class TestHelpScreen:
    """Tests for the help modal screen."""

    @pytest.mark.unit
    def test_keybindings_text_content(self) -> None:
        """Test that the keybindings text contains expected shortcuts."""
        assert "Dashboard" in KEYBINDINGS_TEXT
        assert "Tasks" in KEYBINDINGS_TEXT
        assert "Workers" in KEYBINDINGS_TEXT
        assert "Queues" in KEYBINDINGS_TEXT
        assert "Refresh" in KEYBINDINGS_TEXT
        assert "Quit" in KEYBINDINGS_TEXT

    @pytest.mark.unit
    def test_help_screen_has_bindings(self) -> None:
        """Test that help screen has close bindings."""
        from textual.binding import Binding

        binding_keys: list[str] = []
        for b in HelpScreen.BINDINGS:
            if isinstance(b, Binding):
                binding_keys.append(b.key)
            else:
                # It's a tuple (key, action, description)
                binding_keys.append(b[0])

        assert "escape" in binding_keys
        assert "q" in binding_keys
        assert "?" in binding_keys

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_help_screen_composition(self) -> None:
        """Test that help screen composes correctly."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            # Push help screen and wait for it to be composed
            await pilot.press("?")
            await pilot.pause()

            # Check components
            assert app.screen.query_one("#help-dialog") is not None
            assert app.screen.query_one("#help-title") is not None
            assert app.screen.query_one("#help-content") is not None
            assert app.screen.query_one("#help-close-btn") is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_help_screen_close_on_escape(self) -> None:
        """Test that pressing Escape dismisses help screen."""
        app = AsyncTasQMonitorTUI()
        async with app.run_test() as pilot:
            # Push help screen and wait for it to be composed
            await pilot.press("?")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)

            # Press Escape to close
            await pilot.press("escape")
            await pilot.pause()

            # Should be dismissed
            assert not isinstance(app.screen, HelpScreen)
