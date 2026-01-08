"""
Nutrition API endpoints.
"""

from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas.nutrition import (
    DailyNutritionResponse,
    MealBreakdownResponse,
    NutritionEntryResponse,
    NutritionSummaryResponse,
    NutritionGoalResponse,
    NutritionGoalsListResponse,
    CalorieDeficitResponse,
    CalorieDeficitDayResponse,
    NutritionTrendResponse,
)
from src.db.models import (
    User,
    NutritionLog,
    DailyNutritionSummary,
    NutritionGoal,
    ActivityMetric,
)

router = APIRouter()

DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _get_goal_for_date(
    db: Session, user_id: int, target_date: date
) -> NutritionGoal | None:
    """Get the nutrition goal for a specific date based on day of week."""
    # Python weekday: Monday=0, Sunday=6 (matches our schema)
    day_of_week = target_date.weekday()

    return (
        db.query(NutritionGoal)
        .filter(
            NutritionGoal.user_id == user_id,
            NutritionGoal.day_of_week == day_of_week,
        )
        .first()
    )


@router.get("/daily/{target_date}", response_model=DailyNutritionResponse)
def get_daily_nutrition(
    target_date: date = Path(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_database),
):
    """
    Get nutrition summary for a specific date.

    Returns daily totals, meal breakdown, and comparison to goal.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or compute daily summary
    summary = (
        db.query(DailyNutritionSummary)
        .filter(
            DailyNutritionSummary.user_id == user.id,
            DailyNutritionSummary.date == target_date,
        )
        .first()
    )

    if not summary:
        # Return empty response if no data
        return DailyNutritionResponse(date=target_date)

    # Get goal for this day
    goal = _get_goal_for_date(db, int(user.id), target_date)

    # Calculate variances
    calorie_variance = None
    protein_variance = None
    if goal and summary.total_calories is not None:
        calorie_variance = Decimal(str(summary.total_calories)) - Decimal(
            str(goal.calorie_target)
        )
    if goal and summary.total_protein_g is not None:
        protein_variance = Decimal(str(summary.total_protein_g)) - Decimal(
            str(goal.protein_target_g)
        )

    return DailyNutritionResponse(
        date=summary.date,  # type: ignore[arg-type]
        total_calories=summary.total_calories,
        total_protein_g=summary.total_protein_g,
        total_carbohydrates_g=summary.total_carbohydrates_g,
        total_fat_g=summary.total_fat_g,
        total_fiber_g=summary.total_fiber_g,
        total_sugar_g=summary.total_sugar_g,
        total_sodium_mg=summary.total_sodium_mg,
        breakfast_calories=summary.breakfast_calories,
        lunch_calories=summary.lunch_calories,
        dinner_calories=summary.dinner_calories,
        snacks_calories=summary.snacks_calories,
        meal_count=summary.meal_count,  # type: ignore[arg-type]
        entry_count=summary.entry_count,  # type: ignore[arg-type]
        calorie_target=goal.calorie_target if goal else None,  # type: ignore[arg-type]
        protein_target_g=goal.protein_target_g if goal else None,  # type: ignore[arg-type]
        calorie_variance=calorie_variance,
        protein_variance=protein_variance,
    )


@router.get("/meals/{target_date}", response_model=MealBreakdownResponse)
def get_meals_for_date(
    target_date: date = Path(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_database),
):
    """
    Get meal breakdown for a specific date.

    Returns entries grouped by meal type.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logs = (
        db.query(NutritionLog)
        .filter(
            NutritionLog.user_id == user.id,
            NutritionLog.date == target_date,
        )
        .order_by(NutritionLog.time.nullsfirst(), NutritionLog.meal)
        .all()
    )

    # Group by meal
    meals: dict[str, list[NutritionEntryResponse]] = defaultdict(list)
    total_calories = Decimal("0")
    total_protein = Decimal("0")

    for log in logs:
        entry = NutritionEntryResponse.model_validate(log)
        meals[str(log.meal)].append(entry)
        if log.calories:
            total_calories += Decimal(str(log.calories))
        if log.protein_g:
            total_protein += Decimal(str(log.protein_g))

    return MealBreakdownResponse(
        date=target_date,
        meals=dict(meals),
        total_calories=total_calories,
        total_protein_g=total_protein,
    )


@router.get("/summary", response_model=NutritionSummaryResponse)
def get_nutrition_summary(
    days: int = Query(default=7, ge=1, le=90, description="Days to summarize"),
    db: Session = Depends(get_database),
):
    """
    Get nutrition summary over date range.

    Returns averages, totals, and goal adherence.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    summaries = (
        db.query(DailyNutritionSummary)
        .filter(
            DailyNutritionSummary.user_id == user.id,
            DailyNutritionSummary.date >= start_date,
            DailyNutritionSummary.date <= end_date,
        )
        .all()
    )

    if not summaries:
        return NutritionSummaryResponse(days=days, days_tracked=0)

    # Calculate averages
    days_tracked = len(summaries)
    total_cals = sum(float(s.total_calories or 0) for s in summaries)
    total_protein = sum(float(s.total_protein_g or 0) for s in summaries)
    total_carbs = sum(float(s.total_carbohydrates_g or 0) for s in summaries)
    total_fat = sum(float(s.total_fat_g or 0) for s in summaries)

    # Goal adherence calculation
    days_over = 0
    days_under = 0
    days_on_target = 0
    target_sum: float = 0
    target_count = 0

    for summary in summaries:
        goal = _get_goal_for_date(db, int(user.id), summary.date)  # type: ignore[arg-type]
        if goal and summary.total_calories is not None:
            target = float(goal.calorie_target)
            actual = float(summary.total_calories)
            target_sum += target
            target_count += 1

            variance_pct = abs(actual - target) / target * 100
            if variance_pct <= 10:
                days_on_target += 1
            elif actual > target:
                days_over += 1
            else:
                days_under += 1

    goal_adherence = None
    avg_target = None
    if target_count > 0:
        goal_adherence = Decimal(str(days_on_target / target_count * 100))
        avg_target = Decimal(str(target_sum / target_count))

    return NutritionSummaryResponse(
        days=days,
        days_tracked=days_tracked,
        avg_calories=Decimal(str(total_cals / days_tracked)) if days_tracked else None,
        avg_protein_g=(
            Decimal(str(total_protein / days_tracked)) if days_tracked else None
        ),
        avg_carbohydrates_g=(
            Decimal(str(total_carbs / days_tracked)) if days_tracked else None
        ),
        avg_fat_g=Decimal(str(total_fat / days_tracked)) if days_tracked else None,
        total_calories=Decimal(str(total_cals)),
        avg_calorie_target=avg_target,
        goal_adherence_pct=goal_adherence,
        days_over_target=days_over,
        days_under_target=days_under,
        days_on_target=days_on_target,
    )


@router.get("/goals", response_model=NutritionGoalsListResponse)
def get_nutrition_goals(db: Session = Depends(get_database)):
    """Get current nutrition goals by day of week."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    goals = (
        db.query(NutritionGoal)
        .filter(NutritionGoal.user_id == user.id)
        .order_by(NutritionGoal.day_of_week)
        .all()
    )

    goal_responses = []
    for goal in goals:
        dow = int(goal.day_of_week)  # type: ignore[arg-type]
        goal_responses.append(
            NutritionGoalResponse(
                id=int(goal.id),  # type: ignore[arg-type]
                day_of_week=dow,
                day_name=DAY_NAMES[dow] if 0 <= dow <= 6 else "Unknown",
                calorie_target=int(goal.calorie_target),  # type: ignore[arg-type]
                protein_target_g=int(goal.protein_target_g),  # type: ignore[arg-type]
                carb_pct=int(goal.carb_pct) if goal.carb_pct else None,  # type: ignore[arg-type]
                protein_pct=int(goal.protein_pct) if goal.protein_pct else None,  # type: ignore[arg-type]
                fat_pct=int(goal.fat_pct) if goal.fat_pct else None,  # type: ignore[arg-type]
            )
        )

    return NutritionGoalsListResponse(goals=goal_responses)


@router.get("/goals/today", response_model=NutritionGoalResponse)
def get_today_goal(db: Session = Depends(get_database)):
    """Get nutrition goal for today."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    goal = _get_goal_for_date(db, int(user.id), date.today())

    if not goal:
        raise HTTPException(status_code=404, detail="No goal found for today")

    dow = int(goal.day_of_week)  # type: ignore[arg-type]
    return NutritionGoalResponse(
        id=int(goal.id),  # type: ignore[arg-type]
        day_of_week=dow,
        day_name=DAY_NAMES[dow] if 0 <= dow <= 6 else "Unknown",
        calorie_target=int(goal.calorie_target),  # type: ignore[arg-type]
        protein_target_g=int(goal.protein_target_g),  # type: ignore[arg-type]
        carb_pct=int(goal.carb_pct) if goal.carb_pct else None,  # type: ignore[arg-type]
        protein_pct=int(goal.protein_pct) if goal.protein_pct else None,  # type: ignore[arg-type]
        fat_pct=int(goal.fat_pct) if goal.fat_pct else None,  # type: ignore[arg-type]
    )


@router.get("/trends", response_model=NutritionTrendResponse)
def get_nutrition_trends(
    days: int = Query(default=30, ge=7, le=90, description="Days for trends"),
    db: Session = Depends(get_database),
):
    """
    Get nutrition trends over time.

    Returns daily totals for charting and averages.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    summaries = (
        db.query(DailyNutritionSummary)
        .filter(
            DailyNutritionSummary.user_id == user.id,
            DailyNutritionSummary.date >= start_date,
            DailyNutritionSummary.date <= end_date,
        )
        .order_by(DailyNutritionSummary.date)
        .all()
    )

    daily_data = []
    total_cals = Decimal("0")
    total_protein = Decimal("0")
    count = 0

    for summary in summaries:
        goal = _get_goal_for_date(db, int(user.id), summary.date)  # type: ignore[arg-type]
        calorie_variance = None
        if goal and summary.total_calories is not None:
            calorie_variance = Decimal(str(summary.total_calories)) - Decimal(
                str(goal.calorie_target)
            )

        daily_data.append(
            DailyNutritionResponse(
                date=summary.date,  # type: ignore[arg-type]
                total_calories=summary.total_calories,
                total_protein_g=summary.total_protein_g,
                total_carbohydrates_g=summary.total_carbohydrates_g,
                total_fat_g=summary.total_fat_g,
                calorie_target=goal.calorie_target if goal else None,  # type: ignore[arg-type]
                calorie_variance=calorie_variance,
            )
        )

        if summary.total_calories:
            total_cals += Decimal(str(summary.total_calories))
            count += 1
        if summary.total_protein_g:
            total_protein += Decimal(str(summary.total_protein_g))

    avg_cals = total_cals / count if count > 0 else None
    avg_protein = total_protein / count if count > 0 else None

    return NutritionTrendResponse(
        days=days,
        daily_data=daily_data,
        avg_calories=avg_cals,
        avg_protein_g=avg_protein,
    )


@router.get("/deficit", response_model=CalorieDeficitResponse)
def get_calorie_deficit(
    days: int = Query(default=7, ge=1, le=30, description="Days to analyze"),
    db: Session = Depends(get_database),
):
    """
    Calculate calorie deficit using TDEE from activity data.

    TDEE (from energy expenditure) - Calories consumed = Deficit
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    daily_breakdown = []
    total_deficit = Decimal("0")
    total_tdee = Decimal("0")
    total_intake = Decimal("0")
    count = 0

    current_date = start_date
    while current_date <= end_date:
        # Get nutrition intake
        nutrition = (
            db.query(DailyNutritionSummary)
            .filter(
                DailyNutritionSummary.user_id == user.id,
                DailyNutritionSummary.date == current_date,
            )
            .first()
        )

        # Get TDEE (active + resting energy)
        active_energy = (
            db.query(ActivityMetric)
            .filter(
                ActivityMetric.user_id == user.id,
                ActivityMetric.date == current_date,
                ActivityMetric.metric_type == "active_energy",
            )
            .first()
        )

        resting_energy = (
            db.query(ActivityMetric)
            .filter(
                ActivityMetric.user_id == user.id,
                ActivityMetric.date == current_date,
                ActivityMetric.metric_type == "resting_energy",
            )
            .first()
        )

        # Calculate TDEE
        tdee = None
        if active_energy and resting_energy:
            tdee = Decimal(str(active_energy.value)) + Decimal(
                str(resting_energy.value)
            )

        # Get goal
        goal = _get_goal_for_date(db, int(user.id), current_date)

        # Calculate deficit
        deficit = None
        calories_consumed = nutrition.total_calories if nutrition else None
        on_target = False

        if tdee and calories_consumed:
            deficit = tdee - Decimal(str(calories_consumed))
            total_deficit += deficit
            total_tdee += tdee
            total_intake += Decimal(str(calories_consumed))
            count += 1

            # Check if on target (within 10%)
            if goal:
                target = float(goal.calorie_target)  # type: ignore[arg-type]
                variance_pct = abs(float(calories_consumed) - target) / target * 100
                on_target = variance_pct <= 10

        daily_breakdown.append(
            CalorieDeficitDayResponse(
                date=current_date,
                tdee=tdee,
                calories_consumed=calories_consumed,
                deficit=deficit,
                protein_g=nutrition.total_protein_g if nutrition else None,
                calorie_target=goal.calorie_target if goal else None,  # type: ignore[arg-type]
                on_target=on_target,
            )
        )

        current_date += timedelta(days=1)

    return CalorieDeficitResponse(
        days=days,
        daily_breakdown=daily_breakdown,
        avg_deficit=total_deficit / count if count > 0 else None,
        total_deficit=total_deficit,
        avg_tdee=total_tdee / count if count > 0 else None,
        avg_intake=total_intake / count if count > 0 else None,
    )
