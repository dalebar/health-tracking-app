#!/usr/bin/env python3
"""
Import heart rate metrics (resting HR, walking HR, HRV) from Apple Health.
"""

import time
from pathlib import Path

from src.db.models import User, HeartRateMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    ImportResult,
    create_import_result,
    import_records,
    display_import_summary,
    display_section_header,
)


def main(export_path: Path | None = None) -> ImportResult:
    """
    Import heart rate metrics from Apple Health export.

    This script imports 3 metrics:
    - Resting heart rate (990 records)
    - Walking heart rate (926 records)
    - HRV - Heart Rate Variability (8,244 records → daily averages)

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        ImportResult with import statistics for all 3 metrics.
    """
    start_time = time.time()

    try:
        display_section_header("Apple Health Heart Rate Metrics Import")

        # Default path for backward compatibility (CLI usage)
        if export_path is None:
            export_path = Path(
                "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
            )

        if not export_path.exists():
            return create_import_result(
                script_name="import_heart_rate_metrics",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - start_time,
            )

        parser = AppleHealthParser()

        with get_db_context() as db:
            user = db.query(User).first()
            if not user:
                return create_import_result(
                    script_name="import_heart_rate_metrics",
                    success=False,
                    error_message="No user found. Run insert_initial_data.py first.",
                    duration_seconds=time.time() - start_time,
                )
            user_id = int(user.id)  # type: ignore[arg-type]

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
                records=resting_hr_records,  # type: ignore[arg-type]
                model_class=HeartRateMetric,
                filter_keys=["metric_type", "date"],
                metric_name="Resting HR",
            )
            display_import_summary("Resting HR", inserted_r, skipped_r)

            # Walking HR
            inserted_w, skipped_w = import_records(
                db=db,
                user_id=user_id,
                records=walking_hr_records,  # type: ignore[arg-type]
                model_class=HeartRateMetric,
                filter_keys=["metric_type", "date"],
                metric_name="Walking HR",
            )
            display_import_summary("Walking HR", inserted_w, skipped_w)

            # HRV
            inserted_h, skipped_h = import_records(
                db=db,
                user_id=user_id,
                records=hrv_records,  # type: ignore[arg-type]
                model_class=HeartRateMetric,
                filter_keys=["metric_type", "date"],
                metric_name="HRV",
            )
            display_import_summary("HRV", inserted_h, skipped_h)

        print()
        print("=" * 70)
        print("RECENT HEART RATE METRICS")
        print("=" * 70)

        with get_db_context() as db:
            user = db.query(User).first()
            if user:
                recent = (
                    db.query(HeartRateMetric)
                    .filter(HeartRateMetric.user_id == user.id)
                    .order_by(HeartRateMetric.date.desc())
                    .limit(30)
                    .all()
                )

                # Group by date
                by_date: dict = {}
                for metric in recent:
                    if metric.date not in by_date:
                        by_date[metric.date] = {}
                    by_date[metric.date][metric.metric_type] = metric.value

                print("Last 10 days:")
                for day in sorted(by_date.keys(), reverse=True)[:10]:
                    metrics = by_date[day]
                    resting = metrics.get("resting_heart_rate", "N/A")
                    walking = metrics.get("walking_heart_rate", "N/A")
                    hrv = metrics.get("heart_rate_variability", "N/A")
                    print(
                        f"  ❤️  {day.strftime('%Y-%m-%d')}: "
                        f"Resting: {resting} bpm, Walking: {walking} bpm, HRV: {hrv} ms"
                    )

        print("=" * 70)
        print()
        print("✅ Heart rate metrics imported successfully!")
        print("❤️  Your cardiovascular health is now tracked")

        # Return success with per-metric breakdown
        duration = time.time() - start_time
        return create_import_result(
            script_name="import_heart_rate_metrics",
            success=True,
            inserted_count=inserted_r + inserted_w + inserted_h,
            skipped_count=skipped_r + skipped_w + skipped_h,
            duration_seconds=duration,
            metrics=[
                {
                    "name": "resting_heart_rate",
                    "inserted": inserted_r,
                    "skipped": skipped_r,
                },
                {
                    "name": "walking_heart_rate",
                    "inserted": inserted_w,
                    "skipped": skipped_w,
                },
                {
                    "name": "heart_rate_variability",
                    "inserted": inserted_h,
                    "skipped": skipped_h,
                },
            ],
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Error: {str(e)}")
        return create_import_result(
            script_name="import_heart_rate_metrics",
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


if __name__ == "__main__":
    main()
