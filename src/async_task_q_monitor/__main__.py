"""CLI entry point for async-task-q-monitor.

Run the monitor server with:
    python -m async_task_q_monitor
    async-task-q-monitor --port 8080
"""

import argparse
import sys


def main() -> int:
    """Run the async-task-q-monitor server."""
    parser = argparse.ArgumentParser(
        prog="async-task-q-monitor",
        description="Web-based monitoring UI for async-task-q task queues",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print(
            "Error: uvicorn is required to run the monitor server.\n"
            "Install it with: pip install 'async-task-q-monitor[standard]' or pip install uvicorn",
            file=sys.stderr,
        )
        return 1

    uvicorn.run(
        "async_task_q_monitor.api.main:create_monitoring_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
