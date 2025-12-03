from fastapi.testclient import TestClient
import pytest


@pytest.mark.integration
def test_list_tasks_basic(app):
    with TestClient(app) as client:
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3


@pytest.mark.integration
def test_list_tasks_with_filters(app):
    with TestClient(app) as client:
        resp = client.get("/api/tasks", params={"status": "failed", "queue": "q1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == "t2"


@pytest.mark.integration
def test_get_task_found(app):
    with TestClient(app) as client:
        resp = client.get("/api/tasks/t1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "t1"


@pytest.mark.integration
def test_get_task_not_found(app):
    with TestClient(app) as client:
        resp = client.get("/api/tasks/missing")
        assert resp.status_code == 404


@pytest.mark.integration
def test_retry_task_success(app):
    with TestClient(app) as client:
        resp = client.post("/api/tasks/t2/retry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"


@pytest.mark.integration
def test_retry_task_fail(app):
    with TestClient(app) as client:
        resp = client.post("/api/tasks/t1/retry")
        assert resp.status_code == 400


@pytest.mark.integration
def test_delete_task_success_and_not_found(app):
    with TestClient(app) as client:
        resp = client.delete("/api/tasks/t1")
        assert resp.status_code == 200
        resp2 = client.delete("/api/tasks/t1")
        assert resp2.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "integration"])
