"""TUI subcommand for asynctasq-monitor.

Starts the Textual-based terminal monitoring UI.

Usage:
    asynctasq-monitor tui
    asynctasq-monitor tui --redis-url redis://localhost:6379
"""

from typing import Annotated

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def tui(
    redis_url: Annotated[
        str,
        typer.Option(
            help="Redis connection URL",
            envvar="ASYNCTASQ_REDIS_URL",
            show_envvar=True,
        ),
    ] = "redis://localhost:6379",
    theme: Annotated[
        str,
        typer.Option(
            help="Color theme (dark/light)",
        ),
    ] = "dark",
    refresh_rate: Annotated[
        float,
        typer.Option(
            help="Refresh rate in seconds",
            min=0.1,
            max=60.0,
        ),
    ] = 1.0,
) -> None:
    """Start the terminal-based monitoring UI.

    A keyboard-driven dashboard for monitoring tasks, workers, and queues
    directly in your terminal. Perfect for SSH sessions.
    """
    import logging

    # Set up logging to see what's happening
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s - %(levelname)s - %(message)s",
        filename="/tmp/asynctasq-monitor.log",
        filemode="w",
    )

    # Configure asynctasq global config so TaskService can access the driver
    from asynctasq.config import set_global_config

    set_global_config(driver="redis", redis_url=redis_url)
    logging.getLogger(__name__).info("Set global config with redis_url=%s", redis_url)

    try:
        from asynctasq_monitor.tui.app import AsyncTasQMonitorTUI
    except ImportError:
        typer.echo(
            "Error: Textual is required for the TUI.\n"
            "Install with: pip install 'asynctasq-monitor[tui]'",
            err=True,
        )
        raise typer.Exit(1) from None

    typer.echo("🖥️  Starting TUI monitor...")

    tui_app = AsyncTasQMonitorTUI(
        redis_url=redis_url,
        theme=theme,
        refresh_rate=refresh_rate,
    )
    tui_app.run()
