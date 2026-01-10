"""
API client for fetching health data from FastAPI backend.
"""

import os
from datetime import date
from typing import Any, Optional

import requests


class HealthAPIClient:
    """Client for Health Tracking API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        """
        Initialize API client.

        Args:
            base_url: API URL. Defaults to HEALTH_API_URL env var or localhost.
            api_key: API key for auth. Defaults to HEALTH_API_KEY env var.
        """
        self.base_url = base_url or os.getenv("HEALTH_API_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("HEALTH_API_KEY", "")

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make GET request to API with optional auth."""
        url = f"{self.base_url}{endpoint}"
        headers: dict[str, str] = {}

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
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

    # Nutrition
    def get_daily_nutrition(self, target_date: date) -> Any:
        """Get nutrition summary for a specific date."""
        return self._get(f"/api/v1/nutrition/daily/{target_date.isoformat()}")

    def get_nutrition_summary(self, days: int = 7) -> Any:
        """Get nutrition summary over date range."""
        return self._get("/api/v1/nutrition/summary", params={"days": days})

    def get_meals_for_date(self, target_date: date) -> Any:
        """Get meal breakdown for a specific date."""
        return self._get(f"/api/v1/nutrition/meals/{target_date.isoformat()}")

    def get_nutrition_goals(self) -> Any:
        """Get nutrition goals by day of week."""
        return self._get("/api/v1/nutrition/goals")

    def get_today_goal(self) -> Any:
        """Get nutrition goal for today."""
        return self._get("/api/v1/nutrition/goals/today")

    def get_nutrition_trends(self, days: int = 30) -> Any:
        """Get nutrition trends over time."""
        return self._get("/api/v1/nutrition/trends", params={"days": days})

    def get_calorie_deficit(self, days: int = 7) -> Any:
        """Get calorie deficit analysis (TDEE - intake)."""
        return self._get("/api/v1/nutrition/deficit", params={"days": days})

    # Energy (TDEE breakdown)
    def get_energy_summary(self, start_date: date, end_date: date) -> Any:
        """Get energy expenditure breakdown."""
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        return self._get("/api/v1/activity/summary", params=params)

    # Supplements
    def get_supplements(self, active_only: bool = True) -> Any:
        """Get list of supplements."""
        return self._get("/api/v1/supplements", params={"active_only": active_only})

    def get_supplement_stack(self) -> Any:
        """Get supplement stack with today's status."""
        return self._get("/api/v1/supplements/stack")

    def get_supplement_status_today(self) -> Any:
        """Get today's supplement status."""
        return self._get("/api/v1/supplements/status/today")

    def get_supplement_status(self, target_date: date) -> Any:
        """Get supplement status for a specific date."""
        return self._get(f"/api/v1/supplements/status/{target_date.isoformat()}")

    def get_supplement_adherence(self, weeks_ago: int = 0) -> Any:
        """Get weekly supplement adherence."""
        return self._get(
            "/api/v1/supplements/adherence/week", params={"weeks_ago": weeks_ago}
        )
