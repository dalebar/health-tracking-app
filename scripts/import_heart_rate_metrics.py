#!/usr/bin/env python3
"""
Import heart rate metrics (resting HR, walking HR, HRV) from Apple Health.
"""

from pathlib import Path

from src.db.models import User, HeartRateMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    import_records,
    display_import_summary,
    display_section_header,
)


def main():
    """Import heart rate metrics from Apple Health export."""

    display_section_header("Apple Health Heart Rate Metrics Import")

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

    # Parse Resting Heart Rate
    print("⏳ Parsing resting heart rate (990 records)...")
    resting_hr_records = parser.parse_resting_heart_rate_from_file(export_path)
    print(f"✅ Found {len(resting_hr_records)} resting HR measurements")

    # Parse Walking Heart Rate
    print("⏳ Parsing walking heart rate (926 records)...")
    walking_hr_records = parser.parse_walking_heart_rate_from_file(export_path)
    print(f"✅ Found {len(walking_hr_records)} walking HR measurements")

    # Parse HRV
    print("⏳ Parsing HRV (8,244 records → daily averages)...")
    hrv_records = parser.parse_hrv_from_file(export_path)
    print(f"✅ Aggregated to {len(hrv_records)} daily HRV averages")
    print()

    # Import all three
    print("💾 Importing to database...")

    with get_db_context() as db:
        # Resting HR
        inserted_r, skipped_r = import_records(
            db=db,
            user_id=user_id,
            records=resting_hr_records,
            model_class=HeartRateMetric,
            filter_keys=["metric_type", "date"],
            metric_name="Resting HR",
        )
        display_import_summary("Resting HR", inserted_r, skipped_r)

        # Walking HR
        inserted_w, skipped_w = import_records(
            db=db,
            user_id=user_id,
            records=walking_hr_records,
            model_class=HeartRateMetric,
            filter_keys=["metric_type", "date"],
            metric_name="Walking HR",
        )
        display_import_summary("Walking HR", inserted_w, skipped_w)

        # HRV
        inserted_h, skipped_h = import_records(
            db=db,
            user_id=user_id,
            records=hrv_records,
            model_class=HeartRateMetric,
            filter_keys=["metric_type", "date"],
            metric_name="HRV",
        )
        display_import_summary("HRV", inserted_h, skipped_h)

    print()
    print("=" * 70)
    print("RECENT HEART RATE SUMMARY")
    print("=" * 70)

    with get_db_context() as db:
        user = db.query(User).first()
        if not user:
            return

        recent = (
            db.query(HeartRateMetric)
            .filter(HeartRateMetric.user_id == user.id)
            .order_by(HeartRateMetric.date.desc())
            .limit(30)  # Last 10 days × 3 metrics
            .all()
        )

        # Group by date
        from collections import defaultdict
        from datetime import date
        from decimal import Decimal
        from typing import TypedDict

        class HRMetricsByDay(TypedDict, total=False):
            """Type for grouped HR metrics by day."""

            resting_hr: Decimal
            walking_hr: Decimal
            hrv: Decimal

        by_date: defaultdict[date, HRMetricsByDay] = defaultdict(dict)  # type: ignore[arg-type]
        for metric in recent:
            by_date[metric.date][metric.metric_type] = metric.value  # type: ignore[index, literal-required, typeddict-item]

        print("Last 10 days:")
        for day in sorted(by_date.keys(), reverse=True)[:10]:
            resting = by_date[day].get("resting_hr", Decimal("0"))
            walking = by_date[day].get("walking_hr", Decimal("0"))
            hrv = by_date[day].get("hrv", Decimal("0"))

            parts = [f"  {day.strftime('%Y-%m-%d')}:"]
            if resting:
                parts.append(f"Resting {resting:>3.0f} bpm")
            if walking:
                parts.append(f"Walking {walking:>3.0f} bpm")
            if hrv:
                parts.append(f"HRV {hrv:>5.1f} ms")

            if len(parts) > 1:  # Has data
                print(" | ".join(parts))

    print("=" * 70)
    print()
    print("✅ Heart rate metrics imported successfully!")


if __name__ == "__main__":
    main()
