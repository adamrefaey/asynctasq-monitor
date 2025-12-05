"""CLI entry point for asynctasq-monitor.

Run the monitor with:
    python -m asynctasq_monitor --help
    asynctasq-monitor web --port 8080
    asynctasq-monitor tui
"""

import sys


def main() -> int:
    """Run the asynctasq-monitor CLI."""
    try:
        from asynctasq_monitor.cli.main import app

        app()
        return 0
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
