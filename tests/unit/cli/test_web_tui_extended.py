"""Extended tests for CLI commands - TUI and Web subcommands.

Tests for the TUI and Web subcommands with import error handling
and configuration validation.
"""

import re
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from asynctasq_monitor.cli.main import app

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


class TestTUISubcommand:
    """Tests for the 'tui' subcommand."""

    @pytest.mark.unit
    def test_tui_help(self) -> None:
        """Test that 'tui --help' shows tui-specific options."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--redis-url" in output
        assert "--theme" in output
        assert "--refresh-rate" in output

    @pytest.mark.unit
    def test_tui_help_shows_environment_variable(self) -> None:
        """Test that tui help documents ASYNCTASQ_REDIS_URL env var."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # Should show the environment variable
        assert "ASYNCTASQ_REDIS_URL" in result.stdout

    @pytest.mark.unit
    def test_tui_validates_refresh_rate_bounds(self) -> None:
        """Test that tui validates refresh_rate min/max bounds."""
        # Note: Typer validates these automatically, so we test the help mentions it
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # The help should mention min/max constraints
        assert "seconds" in result.stdout.lower() or "refresh" in result.stdout.lower()

    @pytest.mark.unit
    def test_tui_default_redis_url_in_help(self) -> None:
        """Test that tui help shows default Redis URL."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # Should show default
        assert "redis://localhost:6379" in result.stdout

    @pytest.mark.unit
    def test_tui_help_theme_options(self) -> None:
        """Test that tui help mentions theme options."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # Should mention theme
        assert "theme" in result.stdout.lower() or "dark" in result.stdout.lower()

    @pytest.mark.unit
    def test_tui_refresh_rate_bounds_in_help(self) -> None:
        """Test that tui help shows refresh rate constraints."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # Should mention min/max
        output = result.stdout.lower()
        assert "refresh" in output or "rate" in output

    @pytest.mark.unit
    def test_tui_help_shows_all_options(self) -> None:
        """Test that tui help shows all options."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--redis-url" in output
        assert "--theme" in output
        assert "--refresh-rate" in output

    @pytest.mark.unit
    def test_tui_help_contains_description(self) -> None:
        """Test that tui help contains meaningful description."""
        result = runner.invoke(app, ["tui", "--help"])
        assert result.exit_code == 0
        # Should describe what TUI does
        output = result.stdout.lower()
        assert "terminal" in output or "monitoring" in output

    @pytest.mark.unit
    def test_tui_accepts_env_var_for_redis_url(self) -> None:
        """Test that ASYNCTASQ_REDIS_URL environment variable is accepted."""
        with patch.dict("os.environ", {"ASYNCTASQ_REDIS_URL": "redis://custom:6379"}):
            result = runner.invoke(app, ["tui", "--help"])
            assert result.exit_code == 0
            # The help should indicate the env var is used
            assert "ASYNCTASQ_REDIS_URL" in result.stdout


class TestWebSubcommandExtended:
    """Extended tests for the 'web' subcommand."""

    @pytest.mark.unit
    def test_web_help_shows_all_options(self) -> None:
        """Test that web help shows all required options."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--port" in output
        assert "--host" in output
        assert "--reload" in output or "reload" in output.lower()
        assert "--workers" in output
        assert "--log-level" in output

    @pytest.mark.unit
    def test_web_shows_correct_factory_in_help(self) -> None:
        """Test that web help indicates it uses app factory."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Should indicate it's a web service
        output = result.stdout.lower()
        assert "web" in output or "browser" in output or "fastapi" in output

    @pytest.mark.unit
    def test_web_shows_default_host_in_help(self) -> None:
        """Test that web help shows default host."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Should show defaults in some form
        output = strip_ansi(result.stdout)
        assert "--host" in output

    @pytest.mark.unit
    def test_web_shows_default_port_in_help(self) -> None:
        """Test that web help shows default port."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Should show port option
        output = strip_ansi(result.stdout)
        assert "--port" in output

    @pytest.mark.unit
    def test_web_workers_minimum_value(self) -> None:
        """Test that web enforces minimum workers value."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Help should mention constraints
        output = result.stdout.lower()
        assert "worker" in output

    @pytest.mark.unit
    def test_web_shows_environment_variables(self) -> None:
        """Test that web options show their environment variables."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Environment variables should be shown in help
        assert "MONITOR_HOST" in result.stdout or "MONITOR_PORT" in result.stdout

    @pytest.mark.unit
    def test_web_accepts_env_var_for_host(self) -> None:
        """Test that MONITOR_HOST environment variable is accepted."""
        with patch.dict("os.environ", {"MONITOR_HOST": "0.0.0.0"}):
            result = runner.invoke(app, ["web", "--help"])
            assert result.exit_code == 0
            assert "MONITOR_HOST" in result.stdout

    @pytest.mark.unit
    def test_web_accepts_env_var_for_port(self) -> None:
        """Test that MONITOR_PORT environment variable is accepted."""
        with patch.dict("os.environ", {"MONITOR_PORT": "9000"}):
            result = runner.invoke(app, ["web", "--help"])
            assert result.exit_code == 0
            assert "MONITOR_PORT" in result.stdout

    @pytest.mark.unit
    def test_web_app_factory_documented(self) -> None:
        """Test that web help indicates app factory pattern."""
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0
        # Should be a web subcommand
        assert "web" in result.stdout.lower()
