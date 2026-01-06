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
from src.utils.import_helpers import (
    import_records,
    display_import_summary,
    display_section_header,
)


class MetricsByDay(TypedDict, total=False):
    """Type for grouped metrics by day."""

    steps: Decimal
    active_energy: Decimal
    exercise_minutes: Decimal


def main():
    """Import activity metrics from Apple Health export."""

    display_section_header("Apple Health Activity Metrics Import")

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
        inserted_e, skipped_e = import_records(
            db=db,
            user_id=user_id,
            records=energy_records,
            model_class=ActivityMetric,
            filter_keys=["metric_type", "date"],
            metric_name="Active Energy",
        )
        display_import_summary("Active Energy", inserted_e, skipped_e)

        # Exercise Minutes
        inserted_ex, skipped_ex = import_records(
            db=db,
            user_id=user_id,
            records=exercise_records,
            model_class=ActivityMetric,
            filter_keys=["metric_type", "date"],
            metric_name="Exercise Minutes",
        )
        display_import_summary("Exercise Minutes", inserted_ex, skipped_ex)

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
