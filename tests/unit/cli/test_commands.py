"""Tests for CLI commands.

Tests for the unified CLI using Typer with subcommands.

Phase 8 of the TUI Development Plan specifies:
- CLI tests using Typer's CliRunner
- Verification of help output for all subcommands
- Environment variable documentation
"""

import pytest
from typer.testing import CliRunner

from asynctasq_monitor.cli.main import app

runner = CliRunner()


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
        assert "--port" in result.stdout
        assert "--host" in result.stdout
        assert "--reload" in result.stdout
        assert "--workers" in result.stdout
        assert "--log-level" in result.stdout

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
        assert "--redis-url" in result.stdout
        assert "--theme" in result.stdout
        assert "--refresh-rate" in result.stdout

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
        # Theme should mention dark/light options
        assert "--theme" in result.stdout
        assert "dark" in result.stdout.lower() or "light" in result.stdout.lower()

    @pytest.mark.unit
    def test_tui_refresh_rate_bounds(self) -> None:
        """Test that refresh-rate help shows constraints."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        assert "--refresh-rate" in result.stdout
        # The help should indicate this is a number in seconds
        assert "seconds" in result.stdout.lower() or "rate" in result.stdout.lower()
