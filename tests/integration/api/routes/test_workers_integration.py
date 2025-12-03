from fastapi.testclient import TestClient
import pytest


@pytest.mark.integration
def test_list_workers_integration(app) -> None:
    """Test listing workers returns expected count from shared fixtures."""
    with TestClient(app) as client:  # type: ignore[call-arg]
        resp = client.get("/api/workers")
        assert resp.status_code == 200
        data = resp.json()
        # sample_workers fixture provides 3 workers
        assert data["total"] == 3
        assert isinstance(data["items"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-m", "integration"])
