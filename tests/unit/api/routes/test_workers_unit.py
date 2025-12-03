from typing import Any, cast

import pytest

from async_task_q_monitor.api.routes.workers import WorkerListResponse, list_workers


@pytest.mark.unit
def test_list_workers_unit() -> None:
    """Unit test that calls the route handler directly and checks return shape."""
    # Access pytest.helpers via a typed cast so static checkers accept it.
    async_run = cast(Any, pytest).helpers.async_run
    result = async_run(list_workers())
    # result should be a WorkerListResponse (Pydantic model)
    assert isinstance(result, WorkerListResponse)
    assert result.items == []
    assert result.total == 0


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "unit"])
