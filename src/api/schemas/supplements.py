"""
Pydantic schemas for supplement tracking API.
"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List


# === Request Schemas ===


class SupplementCreate(BaseModel):
    """Schema for creating a new supplement."""

    name: str = Field(..., max_length=100)
    dosage: Optional[str] = Field(None, max_length=50)
    dosage_unit: Optional[str] = Field(None, max_length=20)
    timing: Optional[str] = Field(None, max_length=50)


class SupplementUpdate(BaseModel):
    """Schema for updating a supplement."""

    name: Optional[str] = Field(None, max_length=100)
    dosage: Optional[str] = Field(None, max_length=50)
    dosage_unit: Optional[str] = Field(None, max_length=20)
    timing: Optional[str] = Field(None, max_length=50)
    active: Optional[bool] = None


# === Response Schemas ===


class SupplementResponse(BaseModel):
    """Response schema for a supplement."""

    id: int
    name: str
    dosage: Optional[str] = None
    dosage_unit: Optional[str] = None
    timing: Optional[str] = None
    active: bool

    class Config:
        from_attributes = True


class SupplementListResponse(BaseModel):
    """Response schema for list of supplements."""

    supplements: List[SupplementResponse]
    total: int
    active_count: int


class SupplementStackResponse(BaseModel):
    """
    Response schema for supplement stack display.
    Shows all active supplements grouped by timing.
    """

    date: date
    morning: List[SupplementResponse]
    evening: List[SupplementResponse]
    other: List[SupplementResponse]
    total_active: int
