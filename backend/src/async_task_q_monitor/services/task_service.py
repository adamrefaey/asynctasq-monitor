"""Service layer that wraps the core dispatcher for the monitoring API."""

from async_task_q.core.dispatcher import get_dispatcher
from async_task_q.drivers.base_driver import BaseDriver
from async_task_q_monitor.models.task import Task, TaskFilters


class TaskService:
    """Wrap the core driver and convert core TaskInfo into Pydantic Task models."""

    _driver: BaseDriver | None

    def __init__(self) -> None:
        """Create a TaskService with no attached driver initially."""
        self._driver = None

    async def get_tasks(
        self,
        filters: TaskFilters,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Fetch tasks from the core driver and convert them to `Task` models."""
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)

        # Call core driver; driver returns (list[TaskInfo], total_count)
        task_infos, total = await self._driver.get_tasks(
            status=filters.status.value if filters.status else None,
            queue=filters.queue,
            worker_id=filters.worker_id,
            limit=limit,
            offset=offset,
        )

        tasks = [Task.from_task_info(ti) for ti in task_infos]
        return tasks, total

    async def get_task_by_id(self, task_id: str) -> Task | None:
        """Return a Task by id or None if not found."""
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)
        task_info = await self._driver.get_task_by_id(task_id)
        if not task_info:
            return None
        return Task.from_task_info(task_info)

    async def retry_task(self, task_id: str) -> bool:
        """Attempt to retry a task via the core driver."""
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)
        return await self._driver.retry_task(task_id)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task via the core driver."""
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)
        return await self._driver.delete_task(task_id)

    def _ensure_driver(self) -> None:
        """Ensure the core driver is available; set `self._driver`.

        Raises:
            RuntimeError: if the dispatcher or driver cannot be obtained.

        """
        if self._driver is None:
            dispatcher = get_dispatcher()
            missing_msg = "Dispatcher driver not available"
            if dispatcher is None or not hasattr(dispatcher, "driver"):
                raise RuntimeError(missing_msg)
            self._driver = dispatcher.driver
