
import pytest
from fastapi.testclient import TestClient
from api.main import app
import runtime.task_store
from unittest.mock import MagicMock

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_task_store(task_store):
    """Override the global task store with the test fixture."""
    original_store = runtime.task_store._task_store
    runtime.task_store._task_store = task_store
    yield
    runtime.task_store._task_store = original_store

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Set up temporary environment variables for testing."""
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["BIODOCKIFY_DATA_DIR"] = temp_dir
        yield
        if "BIODOCKIFY_DATA_DIR" in os.environ:
            del os.environ["BIODOCKIFY_DATA_DIR"]

def test_start_research_task():
    """Test starting a research task."""
    response = client.post("/api/research/start", json={"title": "Test Research", "mode": "local"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "task_id" in data
    assert data["task_id"].startswith("task_")

def test_get_tasks():
    """Test listing tasks."""
    # Create a task via API (which uses the overridden store)
    client.post("/api/research/start", json={"title": "Task A", "mode": "local"})
    client.post("/api/research/start", json={"title": "Task B", "mode": "local"})
    
    response = client.get("/api/research/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 2
    assert tasks[0]["title"] in ["Task A", "Task B"]

def test_get_task_status():
    """Test getting task status."""
    start_resp = client.post("/api/research/start", json={"title": "Status Test", "mode": "local"})
    task_id = start_resp.json()["task_id"]
    
    response = client.get(f"/api/research/status/{task_id}")
    assert response.status_code == 200
    status = response.json()
    assert status["task_id"] == task_id
    assert status["status"] in ["pending", "running", "completed", "failed"]

def test_get_nonexistent_task():
    """Test getting a non-existent task."""
    response = client.get("/api/research/status/fake_id")
    assert response.status_code == 404
