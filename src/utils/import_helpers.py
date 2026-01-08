"""
Utility functions for importing health metrics to database.

Provides reusable import logic to reduce code duplication across import scripts.
"""

from typing import TypeVar, Any, TypedDict
from sqlalchemy.orm import Session
from src.db.models import Base

T = TypeVar("T", bound=Base)


class ImportResult(TypedDict):
    """Result from running an import script."""

    script_name: str  # e.g., "import_weight_history"
    success: bool  # Overall success flag
    inserted_count: int  # Total records inserted
    skipped_count: int  # Total records skipped
    duration_seconds: float  # Execution time
    error_message: str | None  # Error details if failed
    metrics: list[dict[str, Any]]  # For scripts that import multiple metrics


def import_records(
    db: Session,
    user_id: int,
    records: list[dict[str, Any]],
    model_class: type[T],
    filter_keys: list[str],
    batch_size: int = 100,
    metric_name: str = "Records",
) -> tuple[int, int]:
    """
    Import records to database with duplicate checking and batch commits.

    Args:
        db: Database session
        user_id: User ID for all records
        records: List of record dictionaries to import
        model_class: SQLAlchemy model class (e.g., ActivityMetric)
        filter_keys: Keys to use for duplicate checking (e.g., ['metric_type', 'date'])
        batch_size: Number of records to commit at once
        metric_name: Display name for progress messages

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    inserted = 0
    skipped = 0

    for record in records:
        # Build filter conditions for duplicate check
        filters = [getattr(model_class, "user_id") == user_id]
        for key in filter_keys:
            filters.append(getattr(model_class, key) == record[key])

        # Check if record exists
        existing = db.query(model_class).filter(*filters).first()

        if existing:
            skipped += 1
            continue

        # Insert new record
        model_instance = model_class(user_id=user_id, **record)
        db.add(model_instance)
        inserted += 1

        # Batch commit
        if inserted % batch_size == 0:
            db.commit()
            print(f"  {metric_name}: {inserted} records...")

    db.commit()
    return inserted, skipped


def display_import_summary(
    metric_name: str, inserted: int, skipped: int, emoji: str = "✅"
) -> None:
    """Display formatted import summary."""
    print(f"{emoji} {metric_name}: {inserted} inserted, {skipped} skipped")


def display_section_header(title: str, width: int = 70) -> None:
    """Display formatted section header."""
    print()
    print("=" * width)
    print(title)
    print("=" * width)
    print()


def create_import_result(
    script_name: str,
    success: bool,
    inserted_count: int = 0,
    skipped_count: int = 0,
    duration_seconds: float = 0.0,
    error_message: str | None = None,
    metrics: list[dict[str, Any]] | None = None,
) -> ImportResult:
    """
    Create a standardized ImportResult dictionary.

    Reduces boilerplate in import scripts by providing a consistent
    way to create result objects.

    Args:
        script_name: Name of the import script (e.g., "import_weight_history")
        success: Whether the import succeeded
        inserted_count: Number of new records inserted
        skipped_count: Number of duplicate records skipped
        duration_seconds: Time taken to run the import
        error_message: Error details if import failed
        metrics: List of per-metric breakdowns for multi-metric scripts

    Returns:
        ImportResult dictionary with all fields populated
    """
    return {
        "script_name": script_name,
        "success": success,
        "inserted_count": inserted_count,
        "skipped_count": skipped_count,
        "duration_seconds": duration_seconds,
        "error_message": error_message,
        "metrics": metrics or [],
    }
