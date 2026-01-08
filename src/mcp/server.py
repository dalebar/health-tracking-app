"""
MCP Server for Health Tracking API.

Provides tools for Claude to query health data through natural language.
"""

from fastmcp import FastMCP
from datetime import date, timedelta
import requests
from typing import Optional, Any

# Initialize MCP server
mcp = FastMCP("Health Tracking")

# API base URL
API_BASE_URL = "http://localhost:8000"


def _get(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Make GET request to FastAPI backend."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


# ============================================================================
# BODY METRICS TOOLS
# ============================================================================


@mcp.tool()
def get_latest_weight() -> Any:
    """
    Get the most recent weight measurement.

    Returns:
        dict: Latest weight with value, unit, date, and source
    """
    return _get("/api/v1/body/weight/latest")


@mcp.tool()
def get_weight_history(days: int = 30, limit: int = 100) -> Any:
    """
    Get weight measurement history.

    Args:
        days: Number of days to look back (default: 30)
        limit: Maximum number of measurements to return (default: 100)

    Returns:
        dict: Weight measurements with count, latest, earliest
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "limit": limit,
    }

    return _get("/api/v1/body/weight", params=params)


@mcp.tool()
def get_weight_trend(days: int = 30) -> Any:
    """
    Get weight trend analysis with averages and change rate.

    Args:
        days: Number of days for trend analysis (default: 30)

    Returns:
        dict: Current weight, start weight, change, percentage, and averages
    """
    return _get("/api/v1/body/weight/trend", params={"days": days})


# ============================================================================
# ACTIVITY METRICS TOOLS
# ============================================================================


@mcp.tool()
def get_daily_activity(activity_date: str) -> Any:
    """
    Get complete activity breakdown for a specific date.

    Args:
        activity_date: Date in YYYY-MM-DD format (e.g., "2026-01-03")

    Returns:
        dict: Steps, active/resting energy (TDEE), and exercise minutes
    """
    return _get(f"/api/v1/activity/daily/{activity_date}")


@mcp.tool()
def get_activity_summary(days: int = 7) -> Any:
    """
    Get activity summary over a date range.

    Args:
        days: Number of days to summarize (default: 7)

    Returns:
        dict: Total and average steps, energy, and exercise minutes
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    return _get("/api/v1/activity/summary", params=params)


@mcp.tool()
def get_recent_tdee(days: int = 7) -> Any:
    """
    Get Total Daily Energy Expenditure (TDEE) for recent days.
    Useful for analyzing daily calorie burn and creating deficits.

    Args:
        days: Number of recent days to retrieve (default: 7)

    Returns:
        dict: Daily breakdown with active, resting, and total energy
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get daily activity for each day
    daily_data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        try:
            daily = _get(f"/api/v1/activity/daily/{day.isoformat()}")
            if "error" not in daily:
                daily_data.append(daily)
        except Exception:  # nosec B110, B112
            continue

    return {
        "days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily_breakdown": daily_data,
    }


# ============================================================================
# WORKOUT TOOLS
# ============================================================================


@mcp.tool()
def get_workouts(
    workout_type: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
) -> Any:
    """
    Get workout history with optional filtering.

    Args:
        workout_type: Filter by type (e.g., "Boxing", "Running"). None for all types.
        days: Number of days to look back (default: 7)
        limit: Maximum workouts to return (default: 50)

    Returns:
        dict: List of workouts with count, duration, and calories
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    params: dict[str, Any] = {
        "limit": limit,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    if workout_type:
        params["workout_type"] = workout_type

    return _get("/api/v1/workouts", params=params)


@mcp.tool()
def get_workout_by_id(workout_id: int) -> Any:
    """
    Get detailed information about a specific workout.

    Args:
        workout_id: The ID of the workout

    Returns:
        dict: Complete workout details including HR, energy, distance
    """
    return _get(f"/api/v1/workouts/{workout_id}")


@mcp.tool()
def get_workout_stats(days: int = 30) -> Any:
    """
    Get workout statistics grouped by type.

    Args:
        days: Number of days for statistics (default: 30)

    Returns:
        list: Stats for each workout type including count, duration, calories, HR
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    return _get("/api/v1/workouts/stats/by-type", params=params)


@mcp.tool()
def get_boxing_workouts(days: int = 30, limit: int = 100) -> Any:
    """
    Get boxing-specific workouts with performance metrics.
    Optimized for analyzing boxing training patterns.

    Args:
        days: Number of days to look back (default: 30)
        limit: Maximum workouts to return (default: 100)

    Returns:
        dict: Boxing workouts with HR, calories, and duration data
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    params: dict[str, Any] = {
        "workout_type": "Boxing",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "limit": limit,
    }
    return _get("/api/v1/workouts", params=params)


# ============================================================================
# SLEEP TOOLS
# ============================================================================


@mcp.tool()
def get_latest_sleep() -> Any:
    """
    Get most recent sleep session with stage breakdown.

    Returns:
        dict: Latest sleep session with duration and sleep stages
    """
    return _get("/api/v1/sleep/latest")


@mcp.tool()
def get_sleep_history(days: int = 7, limit: int = 30) -> Any:
    """
    Get sleep session history.

    Args:
        days: Number of days to look back (default: 7)
        limit: Maximum sessions to return (default: 30)

    Returns:
        dict: Sleep sessions with duration and stage breakdowns
    """
    params: dict[str, Any] = {
        "days": days,
        "limit": limit,
    }
    return _get("/api/v1/sleep/sessions", params=params)


@mcp.tool()
def get_sleep_summary(days: int = 7) -> Any:
    """
    Get sleep summary with averages over date range.

    Args:
        days: Number of days for summary (default: 7)

    Returns:
        dict: Average total sleep, deep, REM, core, and awake minutes
    """
    return _get("/api/v1/sleep/summary", params={"days": days})


# ============================================================================
# NUTRITION TOOLS
# ============================================================================


@mcp.tool()
def get_daily_nutrition(nutrition_date: str) -> Any:
    """
    Get nutrition summary for a specific date.

    Args:
        nutrition_date: Date in YYYY-MM-DD format (e.g., "2026-01-08")

    Returns:
        dict: Calories, protein, carbs, fat, meal breakdown, and goal comparison
    """
    return _get(f"/api/v1/nutrition/daily/{nutrition_date}")


@mcp.tool()
def get_meals_for_date(meal_date: str) -> Any:
    """
    Get detailed meal breakdown for a specific date.

    Args:
        meal_date: Date in YYYY-MM-DD format (e.g., "2026-01-08")

    Returns:
        dict: Individual food entries grouped by meal (Breakfast, Lunch, Dinner, Snacks)
    """
    return _get(f"/api/v1/nutrition/meals/{meal_date}")


@mcp.tool()
def get_nutrition_summary(days: int = 7) -> Any:
    """
    Get nutrition summary over a date range.

    Args:
        days: Number of days to summarize (default: 7, max: 90)

    Returns:
        dict: Average calories, protein, carbs, fat, and goal adherence
    """
    return _get("/api/v1/nutrition/summary", params={"days": days})


@mcp.tool()
def get_nutrition_goals() -> Any:
    """
    Get current nutrition goals by day of week.

    Returns:
        dict: Calorie and protein targets for each day of the week
    """
    return _get("/api/v1/nutrition/goals")


@mcp.tool()
def get_todays_nutrition_goal() -> Any:
    """
    Get today's specific nutrition goal.

    Returns:
        dict: Today's calorie target, protein target, and macro percentages
    """
    return _get("/api/v1/nutrition/goals/today")


@mcp.tool()
def get_nutrition_trends(days: int = 30) -> Any:
    """
    Get nutrition trends over time for charting.

    Args:
        days: Number of days for trends (default: 30, min: 7, max: 90)

    Returns:
        dict: Daily nutrition data with averages and goal adherence
    """
    return _get("/api/v1/nutrition/trends", params={"days": days})


@mcp.tool()
def get_calorie_deficit(days: int = 7) -> Any:
    """
    Calculate calorie deficit using TDEE from activity data.
    TDEE (Total Daily Energy Expenditure) - Calories consumed = Deficit

    Args:
        days: Number of days to analyze (default: 7, max: 30)

    Returns:
        dict: Daily breakdown of TDEE, intake, and deficit with totals
    """
    return _get("/api/v1/nutrition/deficit", params={"days": days})


# ============================================================================
# CONVENIENCE/ANALYSIS TOOLS
# ============================================================================


@mcp.tool()
def get_weekly_summary() -> Any:
    """
    Get comprehensive summary of the last 7 days.
    Includes weight, activity, sleep, and workout metrics.

    Returns:
        dict: Complete weekly summary across all metrics
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    # Get weight trend
    weight = _get("/api/v1/body/weight/trend", params={"days": 7})

    # Get activity summary
    activity_params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    activity = _get("/api/v1/activity/summary", params=activity_params)

    # Get sleep summary
    sleep = _get("/api/v1/sleep/summary", params={"days": 7})

    # Get workouts
    workout_params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "limit": 100,
    }
    workouts = _get("/api/v1/workouts", params=workout_params)

    # Get workout stats
    stats_params: dict[str, Any] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    workout_stats = _get("/api/v1/workouts/stats/by-type", params=stats_params)

    # Get nutrition summary
    nutrition = _get("/api/v1/nutrition/summary", params={"days": 7})

    # Get calorie deficit
    deficit = _get("/api/v1/nutrition/deficit", params={"days": 7})

    return {
        "weight": weight,
        "activity": activity,
        "sleep": sleep,
        "workouts": workouts,
        "workout_stats": workout_stats,
        "nutrition": nutrition,
        "calorie_deficit": deficit,
    }


@mcp.tool()
def get_progress_to_goal() -> Any:
    """
    Get current progress toward weight loss goal (100 kg by April 2026).

    Returns:
        dict: Current weight, goal, remaining, progress percentage, and pace
    """
    latest = _get("/api/v1/body/weight/latest")
    trend = _get("/api/v1/body/weight/trend", params={"days": 30})

    if "error" in latest or "error" in trend:
        return {"error": "Unable to fetch weight data"}

    current = float(latest["value"])
    goal = 100.0
    starting = 114.5  # Initial weight from Jan 3, 2026

    remaining = current - goal
    lost = starting - current
    progress_pct = (lost / (starting - goal)) * 100

    # Calculate pace (kg per week)
    days_tracked = trend.get("days_tracked", 30)
    change = float(trend["change"])
    pace_per_week = (change / days_tracked) * 7 if days_tracked > 0 else 0

    # Estimate days to goal at current pace
    days_to_goal: int | None
    if pace_per_week < 0:  # Losing weight
        weeks_to_goal = remaining / abs(pace_per_week)
        days_to_goal = int(weeks_to_goal * 7)
    else:
        days_to_goal = None

    return {
        "current_weight_kg": current,
        "goal_weight_kg": goal,
        "starting_weight_kg": starting,
        "weight_lost_kg": lost,
        "weight_remaining_kg": remaining,
        "progress_percentage": round(progress_pct, 1),
        "current_pace_kg_per_week": round(pace_per_week, 2),
        "estimated_days_to_goal": days_to_goal,
        "target_date": "April 2026",
    }


@mcp.tool()
def compare_training_periods(
    period1_days: int = 30,
    period2_days: int = 30,
    gap_days: int = 0,
) -> Any:
    """
    Compare two training periods to analyze changes in performance.
    Useful for pre/post injury analysis or tracking improvements.

    Args:
        period1_days: Length of recent period in days (default: 30)
        period2_days: Length of comparison period in days (default: 30)
        gap_days: Days between periods (default: 0, consecutive periods)

    Returns:
        dict: Comparison of workout frequency, intensity, and calories
    """
    # Period 1: Recent period
    end1 = date.today()
    start1 = end1 - timedelta(days=period1_days)

    # Period 2: Older period
    end2 = start1 - timedelta(days=gap_days)
    start2 = end2 - timedelta(days=period2_days)

    # Get data for both periods
    workouts1_params: dict[str, Any] = {
        "start_date": start1.isoformat(),
        "end_date": end1.isoformat(),
        "limit": 200,
    }
    workouts1 = _get("/api/v1/workouts", params=workouts1_params)

    workouts2_params: dict[str, Any] = {
        "start_date": start2.isoformat(),
        "end_date": end2.isoformat(),
        "limit": 200,
    }
    workouts2 = _get("/api/v1/workouts", params=workouts2_params)

    def analyze_period(data: Any) -> dict[str, Any] | None:
        if "error" in data:
            return None

        workouts = data.get("workouts", [])
        if not workouts:
            return None

        total_duration = sum(float(w["duration_minutes"]) for w in workouts)
        total_calories = sum(
            float(w.get("total_energy_kcal", 0))
            for w in workouts
            if w.get("total_energy_kcal")
        )

        hrs = [w["avg_heart_rate_bpm"] for w in workouts if w.get("avg_heart_rate_bpm")]
        avg_hr = sum(hrs) / len(hrs) if hrs else None

        return {
            "workout_count": len(workouts),
            "total_duration_minutes": total_duration,
            "avg_duration_minutes": total_duration / len(workouts),
            "total_calories": total_calories,
            "avg_calories_per_workout": (
                total_calories / len(workouts) if workouts else 0
            ),
            "avg_heart_rate_bpm": avg_hr,
        }

    period1_stats = analyze_period(workouts1)
    period2_stats = analyze_period(workouts2)

    return {
        "period_1": {
            "date_range": f"{start1.isoformat()} to {end1.isoformat()}",
            "stats": period1_stats,
        },
        "period_2": {
            "date_range": f"{start2.isoformat()} to {end2.isoformat()}",
            "stats": period2_stats,
        },
    }


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
