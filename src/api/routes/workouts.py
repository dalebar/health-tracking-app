"""
Workout API endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TypedDict

from fastapi import APIRouter, Depends, Path, Query, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas.workouts import (
    WorkoutResponse,
    WorkoutListResponse,
    WorkoutStatsResponse,
)
from src.db.models import User, Workout

router = APIRouter()


class WorkoutStats(TypedDict):
    """Type definition for workout statistics aggregation."""

    count: int
    total_duration: Decimal
    total_calories: Decimal
    heart_rates: list[int]


@router.get("", response_model=WorkoutListResponse)
def list_workouts(
    workout_type: Optional[str] = Query(None, description="Filter by workout type"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_database),
):
    """
    List workouts with optional filters.

    Supports filtering by type and date range.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(Workout).filter(Workout.user_id == user.id)

    # Apply filters
    if workout_type:
        query = query.filter(Workout.workout_type == workout_type)
    if start_date:
        query = query.filter(
            Workout.start_time >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.filter(
            Workout.start_time <= datetime.combine(end_date, datetime.max.time())
        )

    # Execute query
    workouts = query.order_by(Workout.start_time.desc()).limit(limit).all()

    # Calculate totals
    total_duration = sum(float(str(w.duration_minutes)) for w in workouts)
    total_calories = sum(
        float(str(w.total_energy_kcal)) if w.total_energy_kcal is not None else 0
        for w in workouts
    )

    # Convert to response models
    workout_responses = [WorkoutResponse.model_validate(w) for w in workouts]

    return WorkoutListResponse(
        workouts=workout_responses,
        count=len(workouts),
        total_duration_minutes=Decimal(str(total_duration)),
        total_calories=Decimal(str(total_calories)),
    )


@router.get("/{workout_id}", response_model=WorkoutResponse)
def get_workout(
    workout_id: int = Path(..., description="Workout ID"),
    db: Session = Depends(get_database),
):
    """Get specific workout by ID."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    workout = (
        db.query(Workout)
        .filter(
            Workout.id == workout_id,
            Workout.user_id == user.id,
        )
        .first()
    )

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    return workout


@router.get("/stats/by-type", response_model=list[WorkoutStatsResponse])
def get_workout_stats_by_type(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    db: Session = Depends(get_database),
):
    """
    Get aggregated workout statistics by type.

    Returns count, duration, calories, and avg heart rate for each workout type.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build base query
    query = db.query(Workout).filter(Workout.user_id == user.id)

    # Apply date filters
    if start_date:
        query = query.filter(
            Workout.start_time >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.filter(
            Workout.start_time <= datetime.combine(end_date, datetime.max.time())
        )

    workouts = query.all()

    # Group by type
    stats_by_type: dict[str, WorkoutStats] = {}
    for workout in workouts:
        wtype = str(workout.workout_type)
        if wtype not in stats_by_type:
            stats_by_type[wtype] = {
                "count": 0,
                "total_duration": Decimal("0"),
                "total_calories": Decimal("0"),
                "heart_rates": [],
            }

        stats_by_type[wtype]["count"] += 1
        stats_by_type[wtype]["total_duration"] += Decimal(str(workout.duration_minutes))

        if workout.total_energy_kcal is not None:
            stats_by_type[wtype]["total_calories"] += Decimal(
                str(workout.total_energy_kcal)
            )

        if workout.avg_heart_rate_bpm is not None:
            stats_by_type[wtype]["heart_rates"].append(
                int(str(workout.avg_heart_rate_bpm))
            )

    # Calculate averages and format response
    results = []
    for wtype, stats in stats_by_type.items():
        avg_hr = None
        if stats["heart_rates"]:
            avg_hr = Decimal(str(sum(stats["heart_rates"]) / len(stats["heart_rates"])))

        results.append(
            WorkoutStatsResponse(
                workout_type=wtype,
                count=stats["count"],
                total_duration_minutes=stats["total_duration"],
                avg_duration_minutes=stats["total_duration"] / stats["count"],
                total_calories=stats["total_calories"],
                avg_calories=(
                    stats["total_calories"] / stats["count"]
                    if stats["count"] > 0
                    else Decimal("0")
                ),
                avg_heart_rate=avg_hr,
            )
        )

    # Sort by count descending
    results.sort(key=lambda x: x.count, reverse=True)

    return results
