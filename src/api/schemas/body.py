"""
Pydantic schemas for body metrics API responses.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class WeightResponse(BaseModel):
    """Response model for weight measurement."""

    id: int
    value: Decimal
    unit: str
    recorded_at: datetime
    source: str | None = None

    model_config = {"from_attributes": True}


class WeightHistoryResponse(BaseModel):
    """Response model for weight history."""

    measurements: list[WeightResponse]
    count: int
    latest: WeightResponse | None = None
    earliest: WeightResponse | None = None


class WeightTrendResponse(BaseModel):
    """Response model for weight trend analysis."""

    current_weight: Decimal
    start_weight: Decimal
    change: Decimal
    change_percentage: Decimal
    average_7_day: Decimal | None = None
    average_30_day: Decimal | None = None
    days_tracked: int
