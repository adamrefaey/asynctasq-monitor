"""Service layer that wraps the core dispatcher for the monitoring API."""

from datetime import UTC, datetime

from asynctasq.core.dispatcher import get_dispatcher
from asynctasq.core.models import TaskInfo
from asynctasq.drivers.base_driver import BaseDriver
from asynctasq.serializers import BaseSerializer, MsgpackSerializer
from asynctasq_monitor.models.task import Task, TaskFilters


class TaskService:
    """Wrap the core driver and convert core TaskInfo into Pydantic Task models."""

    _driver: BaseDriver | None
    _serializer: BaseSerializer | None

    def __init__(self) -> None:
        """Create a TaskService with no attached driver initially."""
        self._driver = None
        self._serializer = None

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

        raw_items, total = await self._driver.get_tasks(
            status=filters.status.value if filters.status else None,
            queue=filters.queue,
            limit=limit,
            offset=offset,
        )

        tasks: list[Task] = []
        for raw_bytes, queue_name, status in raw_items:
            task_info = await self._deserialize_task_bytes(raw_bytes, queue_name, status)
            if task_info:
                tasks.append(Task.from_task_info(task_info))

        return tasks, total

    async def get_task_by_id(self, task_id: str) -> Task | None:
        """Return a Task by id or None if not found."""
        self._ensure_driver()
        if self._driver is None:
            msg = "Driver not initialized"
            raise RuntimeError(msg)
        raw_bytes = await self._driver.get_task_by_id(task_id)
        if not raw_bytes:
            return None
        # We don't have queue/status from get_task_by_id, use defaults
        task_info = await self._deserialize_task_bytes(raw_bytes, "default", "pending")
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
        """Ensure the core driver and serializer are available.

        Raises:
            RuntimeError: if the dispatcher or driver cannot be obtained.

        """
        if self._driver is None:
            dispatcher = get_dispatcher()
            missing_msg = "Dispatcher driver not available"
            if dispatcher is None or not hasattr(dispatcher, "driver"):
                raise RuntimeError(missing_msg)
            self._driver = dispatcher.driver
            # Get serializer from dispatcher or create default
            self._serializer = getattr(dispatcher, "serializer", None) or MsgpackSerializer()

    async def _deserialize_task_bytes(
        self,
        raw_bytes: bytes,
        queue_name: str,
        status: str,
    ) -> TaskInfo | None:
        """Deserialize raw task bytes into a TaskInfo object.

        Args:
            raw_bytes: Msgpack-serialized task data
            queue_name: Queue the task was found in
            status: Task status (pending, running)

        Returns:
            TaskInfo object or None if deserialization fails
        """
        if self._serializer is None:
            self._serializer = MsgpackSerializer()

        try:
            task_dict = await self._serializer.deserialize(raw_bytes)

            # Extract task metadata from the serialized dict
            task_id = task_dict.get("task_id", "")
            task_name = task_dict.get("task_name", "")
            enqueued_at = task_dict.get("enqueued_at")

            # Handle enqueued_at being already a datetime or needing parsing
            if enqueued_at is None:
                enqueued_at = datetime.now(UTC)
            elif isinstance(enqueued_at, str):
                enqueued_at = datetime.fromisoformat(enqueued_at)

            params = task_dict.get("params", {})
            args = params.get("args", [])
            kwargs = params.get("kwargs", {})

            return TaskInfo(
                id=task_id,
                name=task_name,
                queue=queue_name,
                status=status,
                enqueued_at=enqueued_at,
                args=args,
                kwargs=kwargs,
                priority=task_dict.get("priority", 0),
                max_retries=task_dict.get("max_retries", 3),
            )
        except Exception:
            # If deserialization fails, return None and skip this task
            return None
