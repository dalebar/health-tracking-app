"""
API client for fetching health data from FastAPI backend.
"""

import requests
from datetime import date
from typing import Any, Optional


class HealthAPIClient:
    """Client for Health Tracking API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make GET request to API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    # Body Metrics
    def get_latest_weight(self) -> Any:
        """Get most recent weight measurement."""
        return self._get("/api/v1/body/weight/latest")

    def get_weight_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> Any:
        """Get weight history with optional date filtering."""
        params: dict[str, Any] = {"limit": limit}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        return self._get("/api/v1/body/weight", params=params)

    def get_weight_trend(self, days: int = 30) -> Any:
        """Get weight trend analysis."""
        return self._get("/api/v1/body/weight/trend", params={"days": days})

    # Activity Metrics
    def get_daily_activity(self, activity_date: date) -> Any:
        """Get activity breakdown for specific date."""
        return self._get(f"/api/v1/activity/daily/{activity_date.isoformat()}")

    def get_activity_summary(self, start_date: date, end_date: date) -> Any:
        """Get activity summary over date range."""
        params: dict[str, Any] = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        return self._get("/api/v1/activity/summary", params=params)

    # Workouts
    def list_workouts(
        self,
        workout_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
    ) -> Any:
        """List workouts with optional filters."""
        params: dict[str, Any] = {"limit": limit}
        if workout_type:
            params["workout_type"] = workout_type
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        return self._get("/api/v1/workouts", params=params)

    def get_workout(self, workout_id: int) -> Any:
        """Get specific workout by ID."""
        return self._get(f"/api/v1/workouts/{workout_id}")

    def get_workout_stats_by_type(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Any:
        """Get workout statistics grouped by type."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        return self._get("/api/v1/workouts/stats/by-type", params=params)
