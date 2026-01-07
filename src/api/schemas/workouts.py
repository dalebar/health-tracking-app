"""
Pydantic schemas for workouts.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class WorkoutResponse(BaseModel):
    """Response model for workout."""

    id: int
    workout_type: str
    start_time: datetime
    end_time: datetime
    duration_minutes: Decimal
    active_energy_kcal: Decimal | None = None
    basal_energy_kcal: Decimal | None = None
    total_energy_kcal: Decimal | None = None
    distance_km: Decimal | None = None
    avg_heart_rate_bpm: int | None = None
    min_heart_rate_bpm: int | None = None
    max_heart_rate_bpm: int | None = None
    indoor_workout: bool | None = None
    source: str | None = None

    model_config = {"from_attributes": True}


class WorkoutListResponse(BaseModel):
    """Response model for workout list."""

    workouts: list[WorkoutResponse]
    count: int
    total_duration_minutes: Decimal
    total_calories: Decimal


class WorkoutStatsResponse(BaseModel):
    """Response model for workout statistics by type."""

    workout_type: str
    count: int
    total_duration_minutes: Decimal
    avg_duration_minutes: Decimal
    total_calories: Decimal
    avg_calories: Decimal
    avg_heart_rate: Decimal | None = None
