"""
Activity metrics API endpoints.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Path, Query, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas.activity import DailyActivityResponse, ActivitySummaryResponse
from src.db.models import User, ActivityMetric

router = APIRouter()


@router.get("/daily/{date}", response_model=DailyActivityResponse)
def get_daily_activity(
    date: date = Path(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_database),
):
    """
    Get complete activity breakdown for a specific date.

    Includes steps, active/resting energy (TDEE), and exercise minutes.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Query all activity metrics for this date
    metrics = (
        db.query(ActivityMetric)
        .filter(
            ActivityMetric.user_id == user.id,
            ActivityMetric.date == date,
        )
        .all()
    )

    # Build response dictionary
    response: dict[str, Any] = {"date": date}

    for metric in metrics:
        metric_type_str = str(metric.metric_type)
        if metric_type_str == "steps":
            response["steps"] = metric.value
        elif metric_type_str == "active_energy":
            response["active_energy_kcal"] = metric.value
        elif metric_type_str == "resting_energy":
            response["resting_energy_kcal"] = metric.value
        elif metric_type_str == "exercise_minutes":
            response["exercise_minutes"] = metric.value

    # Calculate TDEE if we have both active and resting
    if "active_energy_kcal" in response and "resting_energy_kcal" in response:
        response["total_energy_kcal"] = (
            response["active_energy_kcal"] + response["resting_energy_kcal"]
        )

    return DailyActivityResponse(**response)


@router.get("/summary", response_model=ActivitySummaryResponse)
def get_activity_summary(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    db: Session = Depends(get_database),
):
    """
    Get activity summary over a date range.

    Returns aggregated totals and daily averages.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate date range
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")

    days = (end_date - start_date).days + 1

    # Query metrics in range
    metrics = (
        db.query(ActivityMetric)
        .filter(
            ActivityMetric.user_id == user.id,
            ActivityMetric.date >= start_date,
            ActivityMetric.date <= end_date,
        )
        .all()
    )

    # Aggregate by type
    totals = {
        "steps": Decimal("0"),
        "active_energy": Decimal("0"),
        "exercise_minutes": Decimal("0"),
    }

    for metric in metrics:
        metric_type_str = str(metric.metric_type)
        if metric_type_str in totals:
            totals[metric_type_str] += metric.value

    return ActivitySummaryResponse(
        start_date=start_date,
        end_date=end_date,
        days=days,
        total_steps=totals["steps"],
        avg_steps_per_day=totals["steps"] / days,
        total_active_energy=totals["active_energy"],
        avg_active_energy_per_day=totals["active_energy"] / days,
        total_exercise_minutes=totals["exercise_minutes"],
        avg_exercise_minutes_per_day=totals["exercise_minutes"] / days,
    )
