"""
Supplement tracking API endpoints.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas.supplements import (
    SupplementCreate,
    SupplementUpdate,
    SupplementResponse,
    SupplementListResponse,
    SupplementStackResponse,
)
from src.db.models import User, Supplement

router = APIRouter()


# === List and Stack (must come before /{supplement_id}) ===


@router.get("/", response_model=SupplementListResponse)
def list_supplements(
    active_only: bool = True,
    db: Session = Depends(get_database),
):
    """List all supplements for the user."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(Supplement).filter(Supplement.user_id == user.id)

    if active_only:
        query = query.filter(Supplement.active.is_(True))

    supplements = query.order_by(Supplement.timing, Supplement.name).all()

    active_count = sum(1 for s in supplements if s.active)

    return SupplementListResponse(
        supplements=[SupplementResponse.model_validate(s) for s in supplements],
        total=len(supplements),
        active_count=active_count,
    )


@router.get("/stack", response_model=SupplementStackResponse)
def get_supplement_stack(db: Session = Depends(get_database)):
    """
    Get complete supplement stack grouped by timing.

    Perfect for dashboard display.
    """
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()

    # Get all active supplements
    supplements = (
        db.query(Supplement)
        .filter(Supplement.user_id == user.id, Supplement.active.is_(True))
        .order_by(Supplement.name)
        .all()
    )

    # Group by timing
    morning = []
    evening = []
    other = []

    for supp in supplements:
        response = SupplementResponse.model_validate(supp)
        timing = (supp.timing or "").lower()

        if "morning" in timing or "breakfast" in timing or "am" in timing:
            morning.append(response)
        elif (
            "evening" in timing
            or "night" in timing
            or "bed" in timing
            or "pm" in timing
        ):
            evening.append(response)
        else:
            other.append(response)

    return SupplementStackResponse(
        date=today,
        morning=morning,
        evening=evening,
        other=other,
        total_active=len(supplements),
    )


# === CRUD operations ===


@router.post("/", response_model=SupplementResponse, status_code=201)
def create_supplement(
    supplement: SupplementCreate,
    db: Session = Depends(get_database),
):
    """Create a new supplement."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_supplement = Supplement(
        user_id=user.id,
        name=supplement.name,
        dosage=supplement.dosage,
        dosage_unit=supplement.dosage_unit,
        timing=supplement.timing,
        active=True,
    )

    db.add(db_supplement)
    db.commit()
    db.refresh(db_supplement)

    return SupplementResponse.model_validate(db_supplement)


@router.get("/{supplement_id}", response_model=SupplementResponse)
def get_supplement(
    supplement_id: int = Path(..., description="Supplement ID"),
    db: Session = Depends(get_database),
):
    """Get a specific supplement by ID."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    supplement = (
        db.query(Supplement)
        .filter(Supplement.id == supplement_id, Supplement.user_id == user.id)
        .first()
    )

    if not supplement:
        raise HTTPException(status_code=404, detail="Supplement not found")

    return SupplementResponse.model_validate(supplement)


@router.patch("/{supplement_id}", response_model=SupplementResponse)
def update_supplement(
    supplement_id: int,
    update: SupplementUpdate,
    db: Session = Depends(get_database),
):
    """Update a supplement."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    supplement = (
        db.query(Supplement)
        .filter(Supplement.id == supplement_id, Supplement.user_id == user.id)
        .first()
    )

    if not supplement:
        raise HTTPException(status_code=404, detail="Supplement not found")

    # Update only provided fields
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplement, field, value)

    db.commit()
    db.refresh(supplement)

    return SupplementResponse.model_validate(supplement)


@router.delete("/{supplement_id}", status_code=204)
def delete_supplement(
    supplement_id: int,
    db: Session = Depends(get_database),
):
    """Deactivate a supplement."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    supplement = (
        db.query(Supplement)
        .filter(Supplement.id == supplement_id, Supplement.user_id == user.id)
        .first()
    )

    if not supplement:
        raise HTTPException(status_code=404, detail="Supplement not found")

    # Soft delete - just deactivate
    supplement.active = False  # type: ignore[assignment]
    db.commit()
