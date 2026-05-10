from fastapi.testclient import TestClient
from api.main import app
import pytest

client = TestClient(app)


def test_health_check_structure():
    """
    Verify the /health endpoint returns the correct structure
    (components, status, etc.)
    """
    response = client.get("/api/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "components" in data
    assert "api" in data["components"]
    assert "system" in data["components"]


def test_health_check_system_info():
    """
    Verify system info is being populated (RAM/Disk).
    """
    response = client.get("/api/health/detailed")
    data = response.json()
    system = data["components"]["system"]
    # We can't strict assert values, but keys should exist
    assert "ram_free_gb" in system
    assert "disk_free_gb" in system


def test_settings_endpoint():
    """
    Verify settings can be retrieved.
    """
    response = client.get("/api/settings")
    # It might return empty dict or default config, but should be 200
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_rate_limiter():
    """
    Verify rate limiter middleware allows requests (Integration Test).
    Note: We won't flood it here to avoid slowing down tests,
    but we ensure normal requests pass.
    """
    response = client.get("/health")
    assert response.status_code == 200
