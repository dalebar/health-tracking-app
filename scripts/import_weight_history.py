#!/usr/bin/env python3
"""
Import weight history from Apple Health export to database.
"""

import time
from pathlib import Path

from src.db.models import User, BodyMetric
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
    Import weight measurements from Apple Health export.

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        ImportResult with import statistics and status.
    """
    start_time = time.time()

    try:
        display_section_header("Apple Health Weight Import")

        # Default path for backward compatibility (CLI usage)
        if export_path is None:
            export_path = Path(
                "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
            )

        if not export_path.exists():
            return create_import_result(
                script_name="import_weight_history",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - start_time,
            )

        print(f"📂 Reading: {export_path}")
        print(f"📊 File size: {export_path.stat().st_size / (1024**3):.2f} GB")
        print()

        print("⏳ Parsing weight records (this may take 30-60 seconds)...")
        parser = AppleHealthParser()
        weight_records = parser.parse_weight_from_file(export_path)

        print(f"✅ Found {len(weight_records)} weight measurements")
        print()

        if not weight_records:
            return create_import_result(
                script_name="import_weight_history",
                success=True,
                inserted_count=0,
                skipped_count=0,
                duration_seconds=time.time() - start_time,
                error_message="No weight records found in export",
            )

        oldest = weight_records[0]["recorded_at"]
        newest = weight_records[-1]["recorded_at"]
        print(
            f"📅 Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
        )
        print()

        print("💾 Importing to database...")

        with get_db_context() as db:
            user = db.query(User).first()

            if not user:
                return create_import_result(
                    script_name="import_weight_history",
                    success=False,
                    error_message="No user found. Run insert_initial_data.py first.",
                    duration_seconds=time.time() - start_time,
                )

            user_id = user.id  # Store ID before session closes

            inserted_count, skipped_count = import_records(
                db=db,
                user_id=user_id,
                records=weight_records,
                model_class=BodyMetric,
                filter_keys=["metric_type", "recorded_at"],
                metric_name="Weight",
            )

        print()
        display_import_summary("Weight", inserted_count, skipped_count)
        print()

        print("=" * 70)
        print("WEIGHT TREND SUMMARY")
        print("=" * 70)

        with get_db_context() as db:
            user = db.query(User).first()  # Query user again in new session

            if not user:
                print("❌ No user found for weight trend summary.")
            else:
                all_weights = (
                    db.query(BodyMetric)
                    .filter(
                        BodyMetric.user_id == user.id,
                        BodyMetric.metric_type == "weight",
                    )
                    .order_by(BodyMetric.recorded_at)
                    .all()
                )

                if len(all_weights) >= 2:
                    first_weight = all_weights[0]
                    last_weight = all_weights[-1]

                    weight_change = float(last_weight.value) - float(first_weight.value)
                    sign = "+" if weight_change > 0 else ""

                    print(
                        f"First recorded:  {first_weight.recorded_at.strftime('%Y-%m-%d')}: {first_weight.value} kg"
                    )
                    print(
                        f"Most recent:     {last_weight.recorded_at.strftime('%Y-%m-%d')}: {last_weight.value} kg"
                    )
                    print(f"Total change:    {sign}{weight_change:.1f} kg")
                    print()

                    print("Last 10 measurements:")
                    for weight in all_weights[-10:]:
                        print(
                            f"  📊 {weight.recorded_at.strftime('%Y-%m-%d')}: {weight.value} kg"
                        )

        print("=" * 70)
        print()
        print("✅ Weight history imported successfully!")
        print("🎯 Goal: Reach 100kg by April 2026")

        # Return success
        duration = time.time() - start_time
        return create_import_result(
            script_name="import_weight_history",
            success=True,
            inserted_count=inserted_count,
            skipped_count=skipped_count,
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Error: {str(e)}")
        return create_import_result(
            script_name="import_weight_history",
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


if __name__ == "__main__":
    main()
