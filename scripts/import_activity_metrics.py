#!/usr/bin/env python3
"""
Import activity metrics (active energy and exercise minutes) from Apple Health.
"""

import time
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TypedDict

from src.db.models import User, ActivityMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    ImportResult,
    create_import_result,
    import_records,
    display_import_summary,
    display_section_header,
)


class MetricsByDay(TypedDict, total=False):
    """Type for grouped metrics by day."""

    steps: Decimal
    active_energy: Decimal
    exercise_minutes: Decimal


def main(export_path: Path | None = None) -> ImportResult:
    """
    Import activity metrics from Apple Health export.

    This script imports 2 metrics:
    - Active energy (1.1M+ records → daily totals)
    - Exercise minutes (60K+ records → daily totals)

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        ImportResult with import statistics for both metrics.
    """
    start_time = time.time()

    try:
        display_section_header("Apple Health Activity Metrics Import")

        # Default path for backward compatibility (CLI usage)
        if export_path is None:
            export_path = Path(
                "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
            )

        if not export_path.exists():
            return create_import_result(
                script_name="import_activity_metrics",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - start_time,
            )

        parser = AppleHealthParser()

        with get_db_context() as db:
            user = db.query(User).first()
            if not user:
                return create_import_result(
                    script_name="import_activity_metrics",
                    success=False,
                    error_message="No user found. Run insert_initial_data.py first.",
                    duration_seconds=time.time() - start_time,
                )
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

        # Query recent data grouped by date
        with get_db_context() as db:
            user = db.query(User).first()
            if user:
                recent_metrics = (
                    db.query(ActivityMetric)
                    .filter(
                        ActivityMetric.user_id == user.id,
                        ActivityMetric.metric_type.in_(
                            ["active_energy", "exercise_minutes"]
                        ),
                    )
                    .order_by(ActivityMetric.date.desc())
                    .limit(30)
                    .all()
                )

                # Group by date
                by_date: dict[date, MetricsByDay] = defaultdict(dict)
                for metric in recent_metrics:
                    by_date[metric.date][metric.metric_type] = metric.value  # type: ignore

                print("Last 10 days:")
                for day in sorted(by_date.keys(), reverse=True)[:10]:
                    energy = by_date[day].get("active_energy", 0)
                    exercise = by_date[day].get("exercise_minutes", 0)
                    print(
                        f"  📊 {day.strftime('%Y-%m-%d')}: "
                        f"{energy:,.0f} kcal active, {exercise:,.0f} min exercise"
                    )

        print("=" * 70)
        print()
        print("✅ Activity metrics imported successfully!")
        print("📊 Your activity patterns are now tracked")

        # Return success with per-metric breakdown
        duration = time.time() - start_time
        return create_import_result(
            script_name="import_activity_metrics",
            success=True,
            inserted_count=inserted_e + inserted_ex,
            skipped_count=skipped_e + skipped_ex,
            duration_seconds=duration,
            metrics=[
                {"name": "active_energy", "inserted": inserted_e, "skipped": skipped_e},
                {
                    "name": "exercise_minutes",
                    "inserted": inserted_ex,
                    "skipped": skipped_ex,
                },
            ],
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Error: {str(e)}")
        return create_import_result(
            script_name="import_activity_metrics",
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


if __name__ == "__main__":
    main()
