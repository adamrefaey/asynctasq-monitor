"""Unit tests for worker API routes.

Tests the /api/workers/* endpoints with MockWorkerService from conftest.
Follows pytest best practices and Week 5 implementation specifications.
"""

from httpx import AsyncClient
import pytest

pytestmark = pytest.mark.asyncio


# ============================================================================
# Tests: GET /workers
# ============================================================================


class TestListWorkers:
    """Tests for GET /api/workers endpoint."""

    async def test_list_workers_returns_all_workers(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that listing workers returns all workers."""
        response = await async_client.get("/api/workers")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 3
        assert data["total"] == 3

    async def test_list_workers_with_status_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering workers by status."""
        response = await async_client.get("/api/workers?status=active")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        for worker in data["items"]:
            assert worker["status"] == "active"

    async def test_list_workers_with_queue_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering workers by queue."""
        response = await async_client.get("/api/workers?queue=emails")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        for worker in data["items"]:
            assert "emails" in worker["queues"]

    async def test_list_workers_with_search(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test searching workers by name."""
        response = await async_client.get("/api/workers?search=email")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) >= 1
        assert any("email" in w["name"].lower() for w in data["items"])

    async def test_list_workers_with_is_paused_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering workers by paused state."""
        response = await async_client.get("/api/workers?is_paused=true")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["is_paused"] is True


# ============================================================================
# Tests: GET /workers/{worker_id}
# ============================================================================


class TestGetWorker:
    """Tests for GET /api/workers/{worker_id} endpoint."""

    async def test_get_worker_by_id(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test getting a specific worker by ID."""
        response = await async_client.get("/api/workers/worker-1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "worker-1"
        assert data["name"] == "email-worker"
        assert data["status"] == "active"

    async def test_get_worker_not_found(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test 404 for non-existent worker."""
        response = await async_client.get("/api/workers/nonexistent")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data


# ============================================================================
# Tests: GET /workers/{worker_id}/detail
# ============================================================================


class TestGetWorkerDetail:
    """Tests for GET /api/workers/{worker_id}/detail endpoint."""

    async def test_get_worker_detail(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test getting detailed worker info."""
        response = await async_client.get("/api/workers/worker-1/detail")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "worker-1"
        assert "recent_tasks" in data
        assert "hourly_throughput" in data

    async def test_get_worker_detail_not_found(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test 404 for non-existent worker detail."""
        response = await async_client.get("/api/workers/nonexistent/detail")
        assert response.status_code == 404


# ============================================================================
# Tests: Worker Actions
# ============================================================================


class TestPauseWorker:
    """Tests for POST /api/workers/{worker_id}/pause endpoint."""

    async def test_pause_active_worker(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test pausing an active worker."""
        response = await async_client.post("/api/workers/worker-1/pause")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["worker_id"] == "worker-1"
        assert data["action"] == "pause"

    async def test_pause_offline_worker_fails(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that pausing an offline worker fails with 400."""
        response = await async_client.post("/api/workers/worker-3/pause")
        assert response.status_code == 400

        data = response.json()
        assert "offline" in data["detail"].lower()

    async def test_pause_nonexistent_worker_fails(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that pausing a non-existent worker fails with 404."""
        response = await async_client.post("/api/workers/nonexistent/pause")
        assert response.status_code == 404


class TestResumeWorker:
    """Tests for POST /api/workers/{worker_id}/resume endpoint."""

    async def test_resume_paused_worker(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test resuming a paused worker."""
        response = await async_client.post("/api/workers/worker-2/resume")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["action"] == "resume"

    async def test_resume_non_paused_worker_fails(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that resuming a non-paused worker fails with 400."""
        response = await async_client.post("/api/workers/worker-1/resume")
        assert response.status_code == 400

        data = response.json()
        assert "not paused" in data["detail"].lower()


class TestShutdownWorker:
    """Tests for POST /api/workers/{worker_id}/shutdown endpoint."""

    async def test_shutdown_worker(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test graceful shutdown of a worker."""
        response = await async_client.post("/api/workers/worker-1/shutdown")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["action"] == "shutdown"

    async def test_shutdown_offline_worker_fails(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that shutting down an offline worker fails with 400."""
        response = await async_client.post("/api/workers/worker-3/shutdown")
        assert response.status_code == 400

        data = response.json()
        assert "offline" in data["detail"].lower()


class TestKillWorker:
    """Tests for POST /api/workers/{worker_id}/kill endpoint."""

    async def test_kill_worker(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test killing a worker."""
        response = await async_client.post("/api/workers/worker-1/kill")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["action"] == "kill"

    async def test_kill_worker_with_force(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test force killing a worker."""
        response = await async_client.post("/api/workers/worker-2/kill?force=true")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

    async def test_kill_offline_worker_fails(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test killing an offline worker fails with 400."""
        response = await async_client.post("/api/workers/worker-3/kill")
        assert response.status_code == 400

        data = response.json()
        assert "offline" in data["detail"].lower()

    async def test_kill_nonexistent_worker_fails(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test killing a non-existent worker fails with 404."""
        response = await async_client.post("/api/workers/nonexistent/kill")
        assert response.status_code == 404


# ============================================================================
# Tests: POST /workers/{worker_id}/action
# ============================================================================


class TestWorkerAction:
    """Tests for POST /api/workers/{worker_id}/action endpoint."""

    async def test_perform_action_pause(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test performing pause action via action endpoint."""
        response = await async_client.post(
            "/api/workers/worker-1/action",
            json={"action": "pause"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["action"] == "pause"

    async def test_perform_action_with_force(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test performing action with force flag."""
        response = await async_client.post(
            "/api/workers/worker-1/action",
            json={"action": "kill", "force": True},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


# ============================================================================
# Tests: GET /workers/{worker_id}/logs
# ============================================================================


class TestWorkerLogs:
    """Tests for GET /api/workers/{worker_id}/logs endpoint."""

    async def test_get_worker_logs(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test getting logs from a worker."""
        response = await async_client.get("/api/workers/worker-1/logs")
        assert response.status_code == 200

        data = response.json()
        assert "worker_id" in data
        assert "logs" in data
        assert "total" in data
        assert data["worker_id"] == "worker-1"

    async def test_get_worker_logs_with_level_filter(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test filtering logs by level."""
        response = await async_client.get("/api/workers/worker-1/logs?level=INFO")
        assert response.status_code == 200

        data = response.json()
        for log in data["logs"]:
            assert log["level"] == "INFO"

    async def test_get_worker_logs_with_limit(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test limiting log entries."""
        response = await async_client.get("/api/workers/worker-1/logs?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data["logs"]) <= 5

    async def test_get_logs_for_nonexistent_worker(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test 404 for logs of non-existent worker."""
        response = await async_client.get("/api/workers/nonexistent/logs")
        assert response.status_code == 404


# ============================================================================
# Tests: POST /workers/heartbeat
# ============================================================================


class TestHeartbeat:
    """Tests for POST /api/workers/heartbeat endpoint."""

    async def test_process_heartbeat(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test processing a heartbeat from a worker."""
        response = await async_client.post(
            "/api/workers/heartbeat",
            json={
                "worker_id": "worker-1",
                "status": "active",
                "cpu_usage": 50.0,
                "memory_usage": 60.0,
                "tasks_processed": 100,
                "tasks_failed": 5,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["received"] is True
        assert "timestamp" in data
        assert "should_pause" in data
        assert "should_shutdown" in data

    async def test_heartbeat_with_current_task(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test heartbeat with current task info."""
        response = await async_client.post(
            "/api/workers/heartbeat",
            json={
                "worker_id": "worker-1",
                "status": "active",
                "current_task_id": "task-123",
                "current_task_name": "send_email",
                "cpu_usage": 75.0,
                "memory_usage": 80.0,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["received"] is True

    async def test_heartbeat_missing_task_name_fails(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test that heartbeat with task ID but no name fails validation."""
        response = await async_client.post(
            "/api/workers/heartbeat",
            json={
                "worker_id": "worker-1",
                "status": "active",
                "current_task_id": "task-123",
                # missing current_task_name
            },
        )
        # Pydantic validation should fail
        assert response.status_code == 422
