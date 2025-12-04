from typing import Any, cast

import pytest

from asynctasq_monitor.models.worker import WorkerListResponse


@pytest.mark.unit
def test_list_workers_unit(mock_worker_service: Any) -> None:
    """Unit test that calls the mock worker service directly and checks return shape."""
    # Access pytest.helpers via a typed cast so static checkers accept it.
    async_run = cast(Any, pytest).helpers.async_run
    result = async_run(mock_worker_service.get_workers(None))
    # result should be a WorkerListResponse (Pydantic model)
    assert isinstance(result, WorkerListResponse)
    assert len(result.items) == 3
    assert result.total == 3


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "unit"])
