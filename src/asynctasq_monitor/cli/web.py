"""Web subcommand for asynctasq-monitor.

Starts the FastAPI-based web monitoring UI with uvicorn.

Usage:
    asynctasq-monitor web --port 8080
    asynctasq-monitor web --host 0.0.0.0 --reload
"""

from typing import Annotated

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def web(
    host: Annotated[
        str,
        typer.Option(
            help="Host to bind to",
            envvar="MONITOR_HOST",
            show_envvar=True,
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            help="Port to bind to",
            envvar="MONITOR_PORT",
            show_envvar=True,
        ),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option(
            "--reload",
            help="Enable auto-reload for development",
        ),
    ] = False,
    workers: Annotated[
        int,
        typer.Option(
            help="Number of worker processes",
            min=1,
        ),
    ] = 1,
    log_level: Annotated[
        str,
        typer.Option(
            help="Log level",
        ),
    ] = "info",
) -> None:
    """Start the web-based monitoring UI.

    A full-featured dashboard for monitoring tasks, workers, and queues
    in your browser. Built with FastAPI and React.
    """
    try:
        import uvicorn
    except ImportError:
        typer.echo(
            "Error: FastAPI and uvicorn are required for the web UI.\n"
            "Install with: pip install 'asynctasq-monitor[web]'",
            err=True,
        )
        raise typer.Exit(1) from None

    typer.echo(f"🌐 Starting web monitor at http://{host}:{port}")

    uvicorn.run(
        "asynctasq_monitor.api.main:create_monitoring_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level=log_level,
    )
