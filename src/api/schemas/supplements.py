"""
Pydantic schemas for supplement tracking API.
"""

from pydantic import BaseModel, Field
from datetime import date, time
from typing import Optional, List
from decimal import Decimal


# === Request Schemas ===


class SupplementCreate(BaseModel):
    """Schema for creating a new supplement."""

    name: str = Field(..., max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    dosage: Optional[str] = Field(None, max_length=50)
    dosage_unit: Optional[str] = Field(None, max_length=20)
    timing: Optional[str] = Field(None, max_length=50)
    frequency: Optional[str] = Field("daily", max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    purchase_url: Optional[str] = Field(None, max_length=500)

    # Nutritional content (optional)
    vitamin_d_iu: Optional[int] = None
    vitamin_c_mg: Optional[int] = None
    magnesium_mg: Optional[int] = None
    zinc_mg: Optional[Decimal] = None
    omega3_mg: Optional[int] = None
    creatine_g: Optional[Decimal] = None


class SupplementUpdate(BaseModel):
    """Schema for updating a supplement."""

    name: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    dosage: Optional[str] = Field(None, max_length=50)
    dosage_unit: Optional[str] = Field(None, max_length=20)
    timing: Optional[str] = Field(None, max_length=50)
    frequency: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    active: Optional[bool] = None
    notes: Optional[str] = None
    purchase_url: Optional[str] = Field(None, max_length=500)


class SupplementLogCreate(BaseModel):
    """Schema for logging supplement intake."""

    supplement_id: int
    date: date
    taken: bool = True
    taken_at: Optional[time] = None
    dose_count: int = 1
    notes: Optional[str] = None


class SupplementLogBulk(BaseModel):
    """Schema for bulk logging multiple supplements."""

    date: date
    supplement_ids: List[int]
    taken: bool = True


# === Response Schemas ===


class SupplementResponse(BaseModel):
    """Response schema for a supplement."""

    id: int
    name: str
    brand: Optional[str] = None
    dosage: Optional[str] = None
    dosage_unit: Optional[str] = None
    timing: Optional[str] = None
    frequency: Optional[str] = None
    category: Optional[str] = None
    active: bool
    notes: Optional[str] = None

    # Nutritional content
    vitamin_d_iu: Optional[int] = None
    vitamin_c_mg: Optional[int] = None
    magnesium_mg: Optional[int] = None
    zinc_mg: Optional[Decimal] = None
    omega3_mg: Optional[int] = None
    creatine_g: Optional[Decimal] = None

    class Config:
        from_attributes = True


class SupplementListResponse(BaseModel):
    """Response schema for list of supplements."""

    supplements: List[SupplementResponse]
    total: int
    active_count: int


class SupplementLogResponse(BaseModel):
    """Response schema for a supplement log entry."""

    id: int
    supplement_id: int
    supplement_name: str
    date: date
    taken: bool
    taken_at: Optional[time] = None
    dose_count: int
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class DailySupplementStatus(BaseModel):
    """Status of a single supplement for a day."""

    supplement_id: int
    name: str
    dosage: Optional[str] = None
    dosage_unit: Optional[str] = None
    timing: Optional[str] = None
    category: Optional[str] = None
    taken: bool
    taken_at: Optional[time] = None


class DailySupplementsResponse(BaseModel):
    """Response schema for daily supplement status."""

    date: date
    supplements: List[DailySupplementStatus]
    taken_count: int
    total_count: int
    adherence_pct: Decimal


class WeeklyAdherenceResponse(BaseModel):
    """Response schema for weekly supplement adherence."""

    start_date: date
    end_date: date
    supplements: List[dict]  # {name, taken_count, total_days, adherence_pct}
    overall_adherence_pct: Decimal


class SupplementStackResponse(BaseModel):
    """
    Response schema for supplement stack display.
    Shows all active supplements with today's status.
    """

    date: date
    stack: List[DailySupplementStatus]
    taken_today: int
    total_active: int
    week_adherence_pct: Optional[Decimal] = None
