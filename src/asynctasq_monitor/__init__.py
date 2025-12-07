"""AsyncTasQ Monitor package.

Web-based monitoring UI for asynctasq task queues.

Usage:
    # Run the monitor server
    python -m asynctasq_monitor
    asynctasq-monitor --port 8080

    # Or mount in your existing FastAPI app
    from asynctasq_monitor import create_monitoring_app
    app = create_monitoring_app()

Expose a lazy `create_monitoring_app` loader to avoid importing FastAPI
at package import time (helps importing models in environments without
FastAPI installed).

The wrapper imports `asynctasq_monitor.api.main` lazily and returns
the `FastAPI` application instance created by its `create_monitoring_app`
function. The wrapper intentionally avoids importing `fastapi` at
import-time so consumers can import package modules in environments
where FastAPI is not installed.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only import for type checking to avoid a runtime dependency.
    from fastapi import FastAPI  # pragma: no cover - typing only


def create_monitoring_app(*args: object, **kwargs: object) -> "FastAPI":
    """Lazily import and call `create_monitoring_app` from `api.main`.

    Returns a `FastAPI` application instance. Arguments are forwarded to
    the real factory in `asynctasq_monitor.api.main`.
    """
    module = import_module(".api.main", __package__)
    return module.create_monitoring_app(*args, **kwargs)


__all__ = ["create_monitoring_app"]
