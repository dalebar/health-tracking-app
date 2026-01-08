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


# =============================================================================
# Nutrition API Tests
# =============================================================================


def test_get_daily_nutrition():
    """Test getting daily nutrition summary."""
    response = client.get("/api/v1/nutrition/daily/2026-01-04")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert data["date"] == "2026-01-04"
    # Should have nutrition fields even if empty
    assert "total_calories" in data
    assert "total_protein_g" in data


def test_get_daily_nutrition_empty_date():
    """Test getting daily nutrition for date with no data."""
    response = client.get("/api/v1/nutrition/daily/2020-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2020-01-01"
    assert data["total_calories"] is None


def test_get_meals_for_date():
    """Test getting meal breakdown for a date."""
    response = client.get("/api/v1/nutrition/meals/2026-01-04")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "meals" in data
    assert isinstance(data["meals"], dict)


def test_get_nutrition_summary():
    """Test getting nutrition summary over date range."""
    response = client.get("/api/v1/nutrition/summary?days=7")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert data["days"] == 7
    assert "days_tracked" in data
    assert "avg_calories" in data


def test_get_nutrition_goals():
    """Test getting nutrition goals by day of week."""
    response = client.get("/api/v1/nutrition/goals")
    assert response.status_code == 200
    data = response.json()
    assert "goals" in data
    assert isinstance(data["goals"], list)
    # Should have 7 days
    assert len(data["goals"]) == 7
    # Check structure
    if len(data["goals"]) > 0:
        goal = data["goals"][0]
        assert "day_of_week" in goal
        assert "day_name" in goal
        assert "calorie_target" in goal
        assert "protein_target_g" in goal


def test_get_todays_nutrition_goal():
    """Test getting today's nutrition goal."""
    response = client.get("/api/v1/nutrition/goals/today")
    assert response.status_code == 200
    data = response.json()
    assert "calorie_target" in data
    assert "protein_target_g" in data
    assert "day_name" in data


def test_get_nutrition_trends():
    """Test getting nutrition trends."""
    response = client.get("/api/v1/nutrition/trends?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert data["days"] == 30
    assert "daily_data" in data
    assert isinstance(data["daily_data"], list)


def test_get_calorie_deficit():
    """Test getting calorie deficit analysis."""
    response = client.get("/api/v1/nutrition/deficit?days=7")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert data["days"] == 7
    assert "daily_breakdown" in data
    assert isinstance(data["daily_breakdown"], list)
