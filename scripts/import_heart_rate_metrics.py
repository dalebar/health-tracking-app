#!/usr/bin/env python3
"""
Import heart rate metrics (resting HR, walking HR, HRV) from Apple Health.
"""

from pathlib import Path

from src.db.models import User, HeartRateMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser


def import_metric(metric_name, user_id, db, records):
    """Helper to import a heart rate metric type."""
    inserted = 0
    skipped = 0

    for record in records:
        existing = (
            db.query(HeartRateMetric)
            .filter(
                HeartRateMetric.user_id == user_id,
                HeartRateMetric.metric_type == record["metric_type"],
                HeartRateMetric.date == record["date"],
            )
            .first()
        )

        if existing:
            skipped += 1
            continue

        metric = HeartRateMetric(
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
    """Import heart rate metrics from Apple Health export."""

    print("=" * 70)
    print("Apple Health Heart Rate Metrics Import")
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
        inserted_r, skipped_r = import_metric(
            "Resting HR", user_id, db, resting_hr_records
        )
        print(f"✅ Resting HR: {inserted_r} inserted, {skipped_r} skipped")

        # Walking HR
        inserted_w, skipped_w = import_metric(
            "Walking HR", user_id, db, walking_hr_records
        )
        print(f"✅ Walking HR: {inserted_w} inserted, {skipped_w} skipped")

        # HRV
        inserted_h, skipped_h = import_metric("HRV", user_id, db, hrv_records)
        print(f"✅ HRV: {inserted_h} inserted, {skipped_h} skipped")

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
