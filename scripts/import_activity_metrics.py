#!/usr/bin/env python3
"""
Import activity metrics (active energy and exercise minutes) from Apple Health.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TypedDict

from src.db.models import User, ActivityMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser


class MetricsByDay(TypedDict, total=False):
    """Type for grouped metrics by day."""

    steps: Decimal
    active_energy: Decimal
    exercise_minutes: Decimal


def import_metric(parser_method, metric_name, user_id, db, records):
    """Helper to import a metric type."""
    inserted = 0
    skipped = 0

    for record in records:
        existing = (
            db.query(ActivityMetric)
            .filter(
                ActivityMetric.user_id == user_id,
                ActivityMetric.metric_type == record["metric_type"],
                ActivityMetric.date == record["date"],
            )
            .first()
        )

        if existing:
            skipped += 1
            continue

        metric = ActivityMetric(
            user_id=user_id,
            metric_type=record["metric_type"],
            value=record["value"],
            unit=record["unit"],
            date=record["date"],
            recorded_at=record["recorded_at"],
            source=record["source"],
        )
        db.add(metric)
        inserted += 1

        if inserted % 100 == 0:
            db.commit()
            print(f"  {metric_name}: {inserted} records...")

    db.commit()
    return inserted, skipped


def main():
    """Import activity metrics from Apple Health export."""

    print("=" * 70)
    print("Apple Health Activity Metrics Import")
    print("=" * 70)
    print()

    export_path = Path(
        "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
    )

    if not export_path.exists():
        print(f"❌ Export file not found: {export_path}")
        return

    parser = AppleHealthParser()

    with get_db_context() as db:
        user = db.query(User).first()
        if not user:
            print("❌ No user found")
            return
        user_id = user.id

    # Parse Active Energy
    print("⏳ Parsing active energy (1.1M+ records)...")
    energy_records = parser.parse_active_energy_from_file(export_path)
    print(f"✅ Aggregated to {len(energy_records)} daily totals")

    # Parse Exercise Minutes
    print("⏳ Parsing exercise minutes (60K+ records)...")
    exercise_records = parser.parse_exercise_minutes_from_file(export_path)
    print(f"✅ Aggregated to {len(exercise_records)} daily totals")
    print()

    # Import both
    print("💾 Importing to database...")

    with get_db_context() as db:
        # Active Energy
        inserted_e, skipped_e = import_metric(
            None, "Active Energy", user_id, db, energy_records
        )
        print(f"✅ Active Energy: {inserted_e} inserted, {skipped_e} skipped")

        # Exercise Minutes
        inserted_ex, skipped_ex = import_metric(
            None, "Exercise Minutes", user_id, db, exercise_records
        )
        print(f"✅ Exercise Minutes: {inserted_ex} inserted, {skipped_ex} skipped")

    print()
    print("=" * 70)
    print("RECENT ACTIVITY SUMMARY")
    print("=" * 70)

    with get_db_context() as db:
        user = db.query(User).first()
        if not user:
            return

        recent = (
            db.query(ActivityMetric)
            .filter(ActivityMetric.user_id == user.id)
            .order_by(ActivityMetric.date.desc())
            .limit(30)  # Last 10 days × 3 metrics
            .all()
        )

        # Group by date
        by_date: defaultdict[date, MetricsByDay] = defaultdict(dict)  # type: ignore[arg-type]
        for metric in recent:
            by_date[metric.date][metric.metric_type] = metric.value  # type: ignore[index, literal-required, typeddict-item]

        print("Last 10 days:")
        for day in sorted(by_date.keys(), reverse=True)[:10]:
            steps = by_date[day].get("steps", 0)
            energy = by_date[day].get("active_energy", 0)
            exercise = by_date[day].get("exercise_minutes", 0)
            print(
                f"  {day.strftime('%Y-%m-%d')}: "
                f"{steps:>6,.0f} steps | "
                f"{energy:>5,.0f} kcal | "
                f"{exercise:>3,.0f} min"
            )

    print("=" * 70)
    print()
    print("✅ Activity metrics imported successfully!")


if __name__ == "__main__":
    main()
