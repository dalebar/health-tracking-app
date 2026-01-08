"""
Sleep API endpoints.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas.sleep import (
    SleepSessionResponse,
    SleepHistoryResponse,
    SleepSummaryResponse,
)
from src.db.models import User, SleepSession

router = APIRouter()


@router.get("/latest", response_model=SleepSessionResponse)
def get_latest_sleep(
    db: Session = Depends(get_database),
):
    """Get the most recent sleep session with stage breakdown."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session = (
        db.query(SleepSession)
        .filter(SleepSession.user_id == user.id)
        .order_by(SleepSession.start_time.desc())
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="No sleep sessions found")

    return session


@router.get("/sessions", response_model=SleepHistoryResponse)
def list_sleep_sessions(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    days: Optional[int] = Query(None, ge=1, le=365, description="Days to look back"),
    limit: int = Query(30, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_database),
):
    """
    List sleep sessions with optional filters.

    Supports filtering by date range or number of days back.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(SleepSession).filter(SleepSession.user_id == user.id)

    # Apply date filters
    if days is not None:
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(SleepSession.start_time >= cutoff)
    else:
        if start_date:
            query = query.filter(
                SleepSession.start_time
                >= datetime.combine(start_date, datetime.min.time())
            )
        if end_date:
            query = query.filter(
                SleepSession.start_time
                <= datetime.combine(end_date, datetime.max.time())
            )

    # Execute query
    sessions = query.order_by(SleepSession.start_time.desc()).limit(limit).all()

    # Calculate average duration
    avg_duration = None
    if sessions:
        total = sum(s.total_duration_minutes for s in sessions)
        avg_duration = Decimal(str(total / len(sessions)))

    # Convert to response models
    session_responses = [SleepSessionResponse.model_validate(s) for s in sessions]

    return SleepHistoryResponse(
        sessions=session_responses,
        count=len(sessions),
        avg_duration_minutes=avg_duration,
    )


@router.get("/summary", response_model=SleepSummaryResponse)
def get_sleep_summary(
    days: int = Query(7, ge=1, le=365, description="Days for summary"),
    db: Session = Depends(get_database),
):
    """
    Get sleep summary with averages over date range.

    Returns average total sleep time and stage breakdown.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cutoff = datetime.now() - timedelta(days=days)

    sessions = (
        db.query(SleepSession)
        .filter(
            SleepSession.user_id == user.id,
            SleepSession.start_time >= cutoff,
        )
        .all()
    )

    if not sessions:
        return SleepSummaryResponse(
            avg_total_minutes=Decimal("0"),
            days=days,
            sessions_count=0,
        )

    # Calculate averages
    count = len(sessions)
    avg_total = Decimal(str(sum(s.total_duration_minutes for s in sessions) / count))

    # Stage averages (only include sessions that have stage data)
    deep_values = [s.deep_minutes for s in sessions if s.deep_minutes is not None]
    core_values = [s.core_minutes for s in sessions if s.core_minutes is not None]
    rem_values = [s.rem_minutes for s in sessions if s.rem_minutes is not None]
    awake_values = [s.awake_minutes for s in sessions if s.awake_minutes is not None]

    avg_deep = (
        Decimal(str(sum(deep_values) / len(deep_values))) if deep_values else None
    )
    avg_core = (
        Decimal(str(sum(core_values) / len(core_values))) if core_values else None
    )
    avg_rem = Decimal(str(sum(rem_values) / len(rem_values))) if rem_values else None
    avg_awake = (
        Decimal(str(sum(awake_values) / len(awake_values))) if awake_values else None
    )

    return SleepSummaryResponse(
        avg_total_minutes=avg_total,
        avg_deep_minutes=avg_deep,
        avg_core_minutes=avg_core,
        avg_rem_minutes=avg_rem,
        avg_awake_minutes=avg_awake,
        days=days,
        sessions_count=count,
    )


@router.get("/{session_id}", response_model=SleepSessionResponse)
def get_sleep_session(
    session_id: int = Path(..., description="Sleep session ID"),
    db: Session = Depends(get_database),
):
    """Get specific sleep session by ID."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session = (
        db.query(SleepSession)
        .filter(
            SleepSession.id == session_id,
            SleepSession.user_id == user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Sleep session not found")

    return session
