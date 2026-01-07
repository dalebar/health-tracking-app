"""
Pydantic schemas for activity metrics.
"""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class DailyActivityResponse(BaseModel):
    """Response model for daily activity breakdown."""

    date: date
    steps: Decimal | None = None
    active_energy_kcal: Decimal | None = None
    resting_energy_kcal: Decimal | None = None
    total_energy_kcal: Decimal | None = None  # TDEE
    exercise_minutes: Decimal | None = None


class ActivitySummaryResponse(BaseModel):
    """Response model for activity summary over date range."""

    start_date: date
    end_date: date
    days: int
    total_steps: Decimal
    avg_steps_per_day: Decimal
    total_active_energy: Decimal
    avg_active_energy_per_day: Decimal
    total_exercise_minutes: Decimal
    avg_exercise_minutes_per_day: Decimal
