"""
Tests for API endpoints.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_latest_weight():
    """Test getting latest weight measurement."""
    response = client.get("/api/v1/body/weight/latest")
    assert response.status_code == 200
    data = response.json()
    assert "value" in data
    assert "unit" in data
    assert data["unit"] == "kg"


def test_get_weight_history():
    """Test getting weight history."""
    response = client.get("/api/v1/body/weight?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "measurements" in data
    assert "count" in data
    assert isinstance(data["measurements"], list)


def test_get_daily_activity():
    """Test getting daily activity."""
    response = client.get("/api/v1/activity/daily/2026-01-03")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert data["date"] == "2026-01-03"


def test_list_workouts():
    """Test listing workouts."""
    response = client.get("/api/v1/workouts?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "workouts" in data
    assert "count" in data


def test_list_workouts_filtered_by_type():
    """Test filtering workouts by type."""
    response = client.get("/api/v1/workouts?workout_type=Boxing&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "workouts" in data
    for workout in data["workouts"]:
        assert workout["workout_type"] == "Boxing"


def test_get_workout_stats():
    """Test workout statistics by type."""
    response = client.get("/api/v1/workouts/stats/by-type")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "workout_type" in data[0]
        assert "count" in data[0]
        assert "avg_duration_minutes" in data[0]
