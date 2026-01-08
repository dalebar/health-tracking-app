"""
Pydantic schemas for nutrition API responses.
"""

from datetime import date, time
from decimal import Decimal
from pydantic import BaseModel


class NutritionEntryResponse(BaseModel):
    """Response model for a single nutrition log entry."""

    id: int
    date: date
    meal: str
    time: time | None = None
    calories: Decimal | None = None
    protein_g: Decimal | None = None
    carbohydrates_g: Decimal | None = None
    fat_g: Decimal | None = None
    fiber_g: Decimal | None = None
    sugar_g: Decimal | None = None

    model_config = {"from_attributes": True}


class DailyNutritionResponse(BaseModel):
    """Response model for daily nutrition summary."""

    date: date
    total_calories: Decimal | None = None
    total_protein_g: Decimal | None = None
    total_carbohydrates_g: Decimal | None = None
    total_fat_g: Decimal | None = None
    total_fiber_g: Decimal | None = None
    total_sugar_g: Decimal | None = None
    total_sodium_mg: Decimal | None = None

    # Meal breakdown
    breakfast_calories: Decimal | None = None
    lunch_calories: Decimal | None = None
    dinner_calories: Decimal | None = None
    snacks_calories: Decimal | None = None

    # Counts
    meal_count: int | None = None
    entry_count: int | None = None

    # Goal comparison (added by API)
    calorie_target: int | None = None
    protein_target_g: int | None = None
    calorie_variance: Decimal | None = None  # positive = over, negative = under
    protein_variance: Decimal | None = None

    model_config = {"from_attributes": True}


class MealBreakdownResponse(BaseModel):
    """Response model for meals on a specific date."""

    date: date
    meals: dict[str, list[NutritionEntryResponse]]
    total_calories: Decimal | None = None
    total_protein_g: Decimal | None = None


class NutritionSummaryResponse(BaseModel):
    """Response model for nutrition summary over a date range."""

    days: int
    days_tracked: int

    avg_calories: Decimal | None = None
    avg_protein_g: Decimal | None = None
    avg_carbohydrates_g: Decimal | None = None
    avg_fat_g: Decimal | None = None

    total_calories: Decimal | None = None

    # Goal adherence
    avg_calorie_target: Decimal | None = None
    goal_adherence_pct: Decimal | None = None  # % of days within 10% of target
    days_over_target: int = 0
    days_under_target: int = 0
    days_on_target: int = 0


class NutritionGoalResponse(BaseModel):
    """Response model for a nutrition goal."""

    id: int
    day_of_week: int
    day_name: str
    calorie_target: int
    protein_target_g: int
    carb_pct: int | None = None
    protein_pct: int | None = None
    fat_pct: int | None = None

    model_config = {"from_attributes": True}


class NutritionGoalsListResponse(BaseModel):
    """Response model for all nutrition goals."""

    goals: list[NutritionGoalResponse]


class CalorieDeficitDayResponse(BaseModel):
    """Response model for a single day's calorie deficit."""

    date: date
    tdee: Decimal | None = None  # From activity/energy data
    calories_consumed: Decimal | None = None
    deficit: Decimal | None = None  # TDEE - consumed (positive = deficit)
    protein_g: Decimal | None = None
    calorie_target: int | None = None
    on_target: bool = False


class CalorieDeficitResponse(BaseModel):
    """Response model for calorie deficit over a date range."""

    days: int
    daily_breakdown: list[CalorieDeficitDayResponse]
    avg_deficit: Decimal | None = None
    total_deficit: Decimal | None = None
    avg_tdee: Decimal | None = None
    avg_intake: Decimal | None = None


class NutritionTrendResponse(BaseModel):
    """Response model for nutrition trends over time."""

    days: int
    daily_data: list[DailyNutritionResponse]
    avg_calories: Decimal | None = None
    avg_protein_g: Decimal | None = None
    goal_adherence_pct: Decimal | None = None
