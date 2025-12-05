"""Main CLI entry point for asynctasq-monitor.

This module provides the unified CLI using Typer with subcommands for:
- web: Web-based monitoring UI (FastAPI + React)
- tui: Terminal-based monitoring UI (Textual)

Usage:
    asynctasq-monitor --help
    asynctasq-monitor web --port 8080
    asynctasq-monitor tui --redis-url redis://localhost:6379
"""

from pathlib import Path
from typing import Annotated

import typer

from asynctasq_monitor.cli import tui, web

app = typer.Typer(
    name="asynctasq-monitor",
    help="[bold cyan]Real-time monitoring[/] for AsyncTasQ task queues",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Add subcommands
app.add_typer(web.app, name="web", help="Start the web-based monitor UI")
app.add_typer(tui.app, name="tui", help="Start the terminal-based monitor UI")


@app.callback()
def main(
    ctx: typer.Context,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option(
            help="Path to config file (TOML)",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
) -> None:
    """AsyncTasQ Monitor - Real-time monitoring for task queues.

    Choose between [bold cyan]web[/] (browser-based) or
    [bold green]tui[/] (terminal-based) interfaces.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config
