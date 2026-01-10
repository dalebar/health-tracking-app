"""
Supplement tracking API endpoints.
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas.supplements import (
    SupplementCreate,
    SupplementUpdate,
    SupplementResponse,
    SupplementListResponse,
    SupplementLogCreate,
    SupplementLogBulk,
    SupplementLogResponse,
    DailySupplementStatus,
    DailySupplementsResponse,
    WeeklyAdherenceResponse,
    SupplementStackResponse,
)
from src.db.models import User, Supplement, SupplementLog

router = APIRouter()


# === Supplement CRUD ===


@router.get("/", response_model=SupplementListResponse)
def list_supplements(
    active_only: bool = Query(
        default=True, description="Only return active supplements"
    ),
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
        brand=supplement.brand,
        dosage=supplement.dosage,
        dosage_unit=supplement.dosage_unit,
        timing=supplement.timing,
        frequency=supplement.frequency,
        category=supplement.category,
        notes=supplement.notes,
        purchase_url=supplement.purchase_url,
        vitamin_d_iu=supplement.vitamin_d_iu,
        vitamin_c_mg=supplement.vitamin_c_mg,
        magnesium_mg=supplement.magnesium_mg,
        zinc_mg=supplement.zinc_mg,
        omega3_mg=supplement.omega3_mg,
        creatine_g=supplement.creatine_g,
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
    """Delete a supplement (or deactivate it)."""
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


# === Logging ===


@router.post("/log", response_model=SupplementLogResponse, status_code=201)
def log_supplement(
    log: SupplementLogCreate,
    db: Session = Depends(get_database),
):
    """Log taking (or missing) a supplement."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify supplement exists
    supplement = (
        db.query(Supplement)
        .filter(Supplement.id == log.supplement_id, Supplement.user_id == user.id)
        .first()
    )
    if not supplement:
        raise HTTPException(status_code=404, detail="Supplement not found")

    # Check for existing log
    existing = (
        db.query(SupplementLog)
        .filter(
            SupplementLog.user_id == user.id,
            SupplementLog.supplement_id == log.supplement_id,
            SupplementLog.date == log.date,
        )
        .first()
    )

    if existing:
        # Update existing log
        existing.taken = log.taken  # type: ignore[assignment]
        existing.taken_at = log.taken_at  # type: ignore[assignment]
        existing.dose_count = log.dose_count  # type: ignore[assignment]
        existing.notes = log.notes  # type: ignore[assignment]
        db.commit()
        db.refresh(existing)
        db_log = existing
    else:
        # Create new log
        db_log = SupplementLog(
            user_id=user.id,
            supplement_id=log.supplement_id,
            date=log.date,
            taken=log.taken,
            taken_at=log.taken_at,
            dose_count=log.dose_count,
            notes=log.notes,
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)

    return SupplementLogResponse(
        id=db_log.id,
        supplement_id=db_log.supplement_id,
        supplement_name=supplement.name,
        date=db_log.date,
        taken=db_log.taken,
        taken_at=db_log.taken_at,
        dose_count=db_log.dose_count,
        notes=db_log.notes,
    )


@router.post("/log/bulk", status_code=201)
def log_supplements_bulk(
    bulk: SupplementLogBulk,
    db: Session = Depends(get_database),
):
    """Log multiple supplements at once."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logged = 0
    for supplement_id in bulk.supplement_ids:
        # Verify supplement exists
        supplement = (
            db.query(Supplement)
            .filter(Supplement.id == supplement_id, Supplement.user_id == user.id)
            .first()
        )
        if not supplement:
            continue

        # Check for existing log
        existing = (
            db.query(SupplementLog)
            .filter(
                SupplementLog.user_id == user.id,
                SupplementLog.supplement_id == supplement_id,
                SupplementLog.date == bulk.date,
            )
            .first()
        )

        if existing:
            existing.taken = bulk.taken  # type: ignore[assignment]
            logged += 1
        else:
            db_log = SupplementLog(
                user_id=user.id,
                supplement_id=supplement_id,
                date=bulk.date,
                taken=bulk.taken,
            )
            db.add(db_log)
            logged += 1

    db.commit()

    return {"logged": logged, "date": bulk.date}


# === Status & Reporting ===


@router.get("/status/today", response_model=DailySupplementsResponse)
def get_today_status(db: Session = Depends(get_database)):
    """Get supplement status for today."""
    return get_daily_status(target_date=date.today(), db=db)


@router.get("/status/{target_date}", response_model=DailySupplementsResponse)
def get_daily_status(
    target_date: date = Path(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_database),
):
    """Get supplement status for a specific date."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all active supplements
    supplements = (
        db.query(Supplement)
        .filter(Supplement.user_id == user.id, Supplement.active.is_(True))
        .order_by(Supplement.timing, Supplement.name)
        .all()
    )

    # Get logs for this date
    logs = (
        db.query(SupplementLog)
        .filter(
            SupplementLog.user_id == user.id,
            SupplementLog.date == target_date,
        )
        .all()
    )

    log_map = {log.supplement_id: log for log in logs}

    statuses = []
    taken_count = 0

    for supp in supplements:
        log = log_map.get(supp.id)
        taken = log.taken if log else False
        if taken:
            taken_count += 1

        statuses.append(
            DailySupplementStatus(
                supplement_id=supp.id,
                name=supp.name,
                dosage=supp.dosage,
                dosage_unit=supp.dosage_unit,
                timing=supp.timing,
                category=supp.category,
                taken=taken,
                taken_at=log.taken_at if log else None,
            )
        )

    total = len(supplements)
    adherence = Decimal(str(taken_count / total * 100)) if total > 0 else Decimal("0")

    return DailySupplementsResponse(
        date=target_date,
        supplements=statuses,
        taken_count=taken_count,
        total_count=total,
        adherence_pct=adherence,
    )


@router.get("/adherence/week", response_model=WeeklyAdherenceResponse)
def get_weekly_adherence(
    weeks_ago: int = Query(
        default=0, ge=0, le=12, description="Weeks ago (0 = current week)"
    ),
    db: Session = Depends(get_database),
):
    """Get supplement adherence for a week."""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate date range
    today = date.today()
    # Find start of week (Monday)
    start_of_week = today - timedelta(days=today.weekday())
    start_date = start_of_week - timedelta(weeks=weeks_ago)
    end_date = start_date + timedelta(days=6)

    # Get active supplements
    supplements = (
        db.query(Supplement)
        .filter(Supplement.user_id == user.id, Supplement.active.is_(True))
        .all()
    )

    # Get all logs in range
    logs = (
        db.query(SupplementLog)
        .filter(
            SupplementLog.user_id == user.id,
            SupplementLog.date >= start_date,
            SupplementLog.date <= end_date,
            SupplementLog.taken.is_(True),
        )
        .all()
    )

    # Count days in range (might be partial week)
    total_days = min(7, (date.today() - start_date).days + 1) if weeks_ago == 0 else 7

    # Calculate adherence per supplement
    log_counts: dict[int, int] = {}
    for log in logs:
        supp_id: int = log.supplement_id  # type: ignore[assignment]
        log_counts[supp_id] = log_counts.get(supp_id, 0) + 1

    supplement_stats = []
    total_taken = 0
    total_possible = 0

    for supp in supplements:
        supp_id_key: int = supp.id  # type: ignore[assignment]
        taken = log_counts.get(supp_id_key, 0)
        adherence = (
            Decimal(str(taken / total_days * 100)) if total_days > 0 else Decimal("0")
        )

        supplement_stats.append(
            {
                "name": supp.name,
                "taken_count": taken,
                "total_days": total_days,
                "adherence_pct": adherence,
            }
        )

        total_taken += taken
        total_possible += total_days

    overall = (
        Decimal(str(total_taken / total_possible * 100))
        if total_possible > 0
        else Decimal("0")
    )

    return WeeklyAdherenceResponse(
        start_date=start_date,
        end_date=end_date,
        supplements=supplement_stats,
        overall_adherence_pct=overall,
    )


@router.get("/stack", response_model=SupplementStackResponse)
def get_supplement_stack(db: Session = Depends(get_database)):
    """
    Get complete supplement stack with today's status.

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
        .order_by(Supplement.timing, Supplement.name)
        .all()
    )

    # Get today's logs
    today_logs = (
        db.query(SupplementLog)
        .filter(
            SupplementLog.user_id == user.id,
            SupplementLog.date == today,
        )
        .all()
    )

    log_map = {log.supplement_id: log for log in today_logs}

    # Get week's logs for adherence
    week_start = today - timedelta(days=6)
    week_logs = (
        db.query(SupplementLog)
        .filter(
            SupplementLog.user_id == user.id,
            SupplementLog.date >= week_start,
            SupplementLog.date <= today,
            SupplementLog.taken.is_(True),
        )
        .all()
    )

    week_taken = len(week_logs)
    week_possible = len(supplements) * 7
    week_adherence = (
        Decimal(str(week_taken / week_possible * 100)) if week_possible > 0 else None
    )

    stack = []
    taken_today = 0

    for supp in supplements:
        log = log_map.get(supp.id)
        taken = log.taken if log else False
        if taken:
            taken_today += 1

        stack.append(
            DailySupplementStatus(
                supplement_id=supp.id,
                name=supp.name,
                dosage=supp.dosage,
                dosage_unit=supp.dosage_unit,
                timing=supp.timing,
                category=supp.category,
                taken=taken,
                taken_at=log.taken_at if log else None,
            )
        )

    return SupplementStackResponse(
        date=today,
        stack=stack,
        taken_today=taken_today,
        total_active=len(supplements),
        week_adherence_pct=week_adherence,
    )
