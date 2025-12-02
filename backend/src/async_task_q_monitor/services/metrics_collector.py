"""Metrics collection helpers used by the monitoring app."""

import asyncio
import contextlib
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Minimal metrics collector used by the app lifespan in tests.

    This is a lightweight stub that starts a background task and can be
    started/stopped asynchronously. The real implementation will poll
    drivers and broadcast via websockets.
    """

    def __init__(self) -> None:
        """Create a new minimal MetricsCollector."""
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event = asyncio.Event()

    async def _run(self) -> None:
        """Run periodic work until stopped."""
        # Use Event.wait with timeout to avoid busy-waiting and be responsive
        while not self._stop_event.is_set():
            await asyncio.wait_for(self._stop_event.wait(), timeout=1)

    async def start(self) -> None:
        """Start the background collector task."""
        self._stop_event.clear()
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run())

    async def stop(self) -> None:
        """Stop the background collector and wait for its cancellation."""
        self._stop_event.set()
        if self._task:
            # Await the task to finish gracefully, suppressing CancelledError
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
