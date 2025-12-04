from typing import Any

import pytest

from asynctasq_monitor.models.task import TaskFilters, TaskStatus


@pytest.mark.unit
def test_mock_task_service_unit(mock_task_service: Any) -> None:
    """Unit test for the MockTaskService behaviour.

    Use a typed Any for the fixture and access the test helper via getattr to
    keep static checkers (pyright) and linters (ruff) satisfied.
    """
    svc: Any = mock_task_service

    # access the helper in a way that static checkers can tolerate
    async_run = pytest.helpers.async_run  # type: ignore[attr-defined]

    # get_tasks no filters
    filters = TaskFilters(search=None)
    items, total = async_run(svc.get_tasks(filters))
    assert total == 4

    # filter by status
    filters = TaskFilters(status=TaskStatus.FAILED, search=None)
    items, total = async_run(svc.get_tasks(filters))
    assert total == 1

    # get_task_by_id
    t = async_run(svc.get_task_by_id("t2"))
    assert t is not None and t.id == "t2"

    # retry only allowed for FAILED
    assert async_run(svc.retry_task("t2")) is True
    assert async_run(svc.retry_task("t1")) is False

    # delete task
    assert async_run(svc.delete_task("t1")) is True
    assert async_run(svc.delete_task("t1")) is False


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "unit"])
