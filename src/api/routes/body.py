"""
Body metrics API endpoints (weight, BMI, body fat).
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas.body import (
    WeightResponse,
    WeightHistoryResponse,
    WeightTrendResponse,
)
from src.db.models import User, BodyMetric

router = APIRouter()


@router.get("/weight", response_model=WeightHistoryResponse)
def get_weight_history(
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: Session = Depends(get_database),
):
    """
    Get weight measurement history.

    Returns weight measurements with optional date range filtering.
    """
    # Get user (assuming single user for now)
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(BodyMetric).filter(
        BodyMetric.user_id == user.id,
        BodyMetric.metric_type == "weight",
    )

    # Apply date filters if provided
    if start_date:
        query = query.filter(
            BodyMetric.recorded_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        query = query.filter(
            BodyMetric.recorded_at <= datetime.combine(end_date, datetime.max.time())
        )

    # Order by date descending and limit
    measurements = query.order_by(BodyMetric.recorded_at.desc()).limit(limit).all()

    if not measurements:
        return WeightHistoryResponse(
            measurements=[],
            count=0,
            latest=None,
            earliest=None,
        )

    # Convert to response models
    weight_responses = [WeightResponse.model_validate(m) for m in measurements]

    return WeightHistoryResponse(
        measurements=weight_responses,
        count=len(measurements),
        latest=weight_responses[0],  # Already sorted desc
        earliest=weight_responses[-1],
    )


@router.get("/weight/latest", response_model=WeightResponse)
def get_latest_weight(db: Session = Depends(get_database)):
    """Get most recent weight measurement."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    weight = (
        db.query(BodyMetric)
        .filter(
            BodyMetric.user_id == user.id,
            BodyMetric.metric_type == "weight",
        )
        .order_by(BodyMetric.recorded_at.desc())
        .first()
    )

    if not weight:
        raise HTTPException(status_code=404, detail="No weight measurements found")

    return weight


@router.get("/weight/trend", response_model=WeightTrendResponse)
def get_weight_trend(
    days: int = Query(
        30, ge=7, le=365, description="Number of days for trend analysis"
    ),
    db: Session = Depends(get_database),
):
    """
    Get weight trend analysis.

    Calculates weight change and averages over specified period.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all weights within period
    cutoff_date = datetime.now() - timedelta(days=days)
    weights = (
        db.query(BodyMetric)
        .filter(
            BodyMetric.user_id == user.id,
            BodyMetric.metric_type == "weight",
            BodyMetric.recorded_at >= cutoff_date,
        )
        .order_by(BodyMetric.recorded_at.asc())
        .all()
    )

    if not weights or len(weights) < 2:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for {days}-day trend (need at least 2 measurements)",
        )

    # Calculate trend
    start_weight = weights[0].value
    current_weight = weights[-1].value
    change = current_weight - start_weight
    change_percentage = (change / start_weight) * 100

    # Calculate rolling averages
    values = [float(w.value) for w in weights]
    avg_7_day = None
    avg_30_day = None

    if len(weights) >= 7:
        avg_7_day = Decimal(str(sum(values[-7:]) / 7))
    if len(weights) >= 30:
        avg_30_day = Decimal(str(sum(values[-30:]) / 30))

    return WeightTrendResponse(
        current_weight=current_weight,
        start_weight=start_weight,
        change=change,
        change_percentage=change_percentage,
        average_7_day=avg_7_day,
        average_30_day=avg_30_day,
        days_tracked=len(weights),
    )
