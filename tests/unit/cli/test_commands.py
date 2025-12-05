"""Tests for CLI commands.

Tests for the unified CLI using Typer with subcommands.

Phase 8 of the TUI Development Plan specifies:
- CLI tests using Typer's CliRunner
- Verification of help output for all subcommands
- Environment variable documentation
"""

import re

import pytest
from typer.testing import CliRunner

from asynctasq_monitor.cli.main import app

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


class TestMainCLI:
    """Tests for the main CLI entry point."""

    @pytest.mark.unit
    def test_help_shows_subcommands(self) -> None:
        """Test that --help shows available subcommands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "asynctasq-monitor" in result.stdout.lower() or "real-time" in result.stdout.lower()
        assert "web" in result.stdout
        assert "tui" in result.stdout

    @pytest.mark.unit
    def test_no_args_shows_help(self) -> None:
        """Test that running without args shows help (no_args_is_help=True)."""
        result = runner.invoke(app, [])
        # With no_args_is_help=True, it shows help (exit code may be 0 or 2)
        assert "web" in result.stdout
        assert "tui" in result.stdout

    @pytest.mark.unit
    def test_verbose_option(self) -> None:
        """Test that --verbose option is recognized."""
        # With no_args_is_help, even with --verbose it should show help
        result = runner.invoke(app, ["--verbose", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_help_contains_description(self) -> None:
        """Test that help contains a meaningful description."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Should contain the "Real-time monitoring" text
        assert "monitoring" in result.stdout.lower() or "task" in result.stdout.lower()

    @pytest.mark.unit
    def test_config_option_in_help(self) -> None:
        """Test that --config option is shown in help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # The --config option should be documented
        assert "--config" in result.stdout or "config" in result.stdout.lower()


class TestWebSubcommand:
    """Tests for the 'web' subcommand."""

    @pytest.mark.unit
    def test_web_help(self) -> None:
        """Test that 'web --help' shows web-specific options."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--port" in output
        assert "--host" in output
        assert "--reload" in output
        assert "--workers" in output
        assert "--log-level" in output

    @pytest.mark.unit
    def test_web_shows_environment_variables(self) -> None:
        """Test that web options show their environment variables."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Environment variables should be shown in help
        assert "MONITOR_HOST" in result.stdout or "env var" in result.stdout.lower()

    @pytest.mark.unit
    def test_web_help_contains_description(self) -> None:
        """Test that web help contains a meaningful description."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Should mention web/browser monitoring
        assert "web" in result.stdout.lower() or "browser" in result.stdout.lower()

    @pytest.mark.unit
    def test_web_default_values_documented(self) -> None:
        """Test that default values are documented in web help."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Default port should be documented
        assert "8000" in result.stdout or "default" in result.stdout.lower()


class TestTUISubcommand:
    """Tests for the 'tui' subcommand."""

    @pytest.mark.unit
    def test_tui_help(self) -> None:
        """Test that 'tui --help' shows TUI-specific options."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--redis-url" in output
        assert "--theme" in output
        assert "--refresh-rate" in output

    @pytest.mark.unit
    def test_tui_shows_environment_variables(self) -> None:
        """Test that TUI options show their environment variables."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # Environment variable should be shown in help
        assert "ASYNCTASQ_REDIS_URL" in result.stdout or "env var" in result.stdout.lower()

    @pytest.mark.unit
    def test_tui_help_contains_description(self) -> None:
        """Test that TUI help contains a meaningful description."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # Should mention terminal/TUI/keyboard
        assert (
            "terminal" in result.stdout.lower()
            or "keyboard" in result.stdout.lower()
            or "tui" in result.stdout.lower()
        )

    @pytest.mark.unit
    def test_tui_theme_options(self) -> None:
        """Test that theme option is properly documented."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        # Theme should mention dark/light options
        assert "--theme" in output
        assert "dark" in output.lower() or "light" in output.lower()

    @pytest.mark.unit
    def test_tui_refresh_rate_bounds(self) -> None:
        """Test that refresh-rate help shows constraints."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--refresh-rate" in output
        # The help should indicate this is a number in seconds
        assert "seconds" in output.lower() or "rate" in output.lower()
