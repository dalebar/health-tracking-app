"""
Pydantic schemas for sleep API responses.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class SleepSessionResponse(BaseModel):
    """Response model for a single sleep session."""

    id: int
    start_time: datetime
    end_time: datetime
    total_duration_minutes: int
    deep_minutes: int | None = None
    core_minutes: int | None = None
    rem_minutes: int | None = None
    awake_minutes: int | None = None
    source: str | None = None

    model_config = {"from_attributes": True}


class SleepHistoryResponse(BaseModel):
    """Response model for sleep history."""

    sessions: list[SleepSessionResponse]
    count: int
    avg_duration_minutes: Decimal | None = None


class SleepSummaryResponse(BaseModel):
    """Response model for sleep summary statistics."""

    avg_total_minutes: Decimal
    avg_deep_minutes: Decimal | None = None
    avg_core_minutes: Decimal | None = None
    avg_rem_minutes: Decimal | None = None
    avg_awake_minutes: Decimal | None = None
    days: int
    sessions_count: int
