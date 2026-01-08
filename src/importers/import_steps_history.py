#!/usr/bin/env python3
"""
Import step count history from Apple Health export to database.
"""

import time
from pathlib import Path

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


def main(export_path: Path | None = None) -> ImportResult:
    """
    Import step counts from Apple Health export.

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        ImportResult with import statistics and status.
    """
    start_time = time.time()

    try:
        display_section_header("Apple Health Steps Import")

        # Default path for backward compatibility (CLI usage)
        if export_path is None:
            export_path = Path(
                "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
            )

        if not export_path.exists():
            return create_import_result(
                script_name="import_steps_history",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - start_time,
            )

        print(f"📂 Reading: {export_path}")
        print(f"📊 File size: {export_path.stat().st_size / (1024**3):.2f} GB")
        print()

        print("⏳ Parsing step records (aggregating 69K+ records by date)...")
        print("   This may take 60-90 seconds...")
        parser = AppleHealthParser()
        step_records = parser.parse_steps_from_file(export_path)

        print(f"✅ Aggregated to {len(step_records)} daily totals")
        print()

        if not step_records:
            return create_import_result(
                script_name="import_steps_history",
                success=True,
                inserted_count=0,
                skipped_count=0,
                duration_seconds=time.time() - start_time,
                error_message="No step records found in export",
            )

        # Display date range
        oldest = step_records[0]["date"]
        newest = step_records[-1]["date"]
        print(
            f"📅 Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
        )

        # Calculate some stats
        total_steps = sum(float(r["value"]) for r in step_records)
        avg_steps = total_steps / len(step_records)
        max_day = max(step_records, key=lambda x: x["value"])

        print(f"📊 Total steps: {total_steps:,.0f}")
        print(f"📊 Average daily: {avg_steps:,.0f} steps")
        print(
            f"🏆 Best day: {max_day['date'].strftime('%Y-%m-%d')} with {max_day['value']:,.0f} steps"
        )
        print()

        # Insert into database
        print("💾 Importing to database...")

        with get_db_context() as db:
            user = db.query(User).first()

            if not user:
                return create_import_result(
                    script_name="import_steps_history",
                    success=False,
                    error_message="No user found. Run insert_initial_data.py first.",
                    duration_seconds=time.time() - start_time,
                )

            user_id = int(user.id)  # type: ignore[arg-type]

            inserted_count, skipped_count = import_records(
                db=db,
                user_id=user_id,
                records=step_records,  # type: ignore[arg-type]
                model_class=ActivityMetric,
                filter_keys=["metric_type", "date"],
                metric_name="Steps",
            )

        print()
        display_import_summary("Steps", inserted_count, skipped_count)
        print()

        # Display recent activity
        print("=" * 70)
        print("RECENT STEP ACTIVITY")
        print("=" * 70)

        with get_db_context() as db:
            user = db.query(User).first()

            if user:
                recent_steps = (
                    db.query(ActivityMetric)
                    .filter(
                        ActivityMetric.user_id == user.id,
                        ActivityMetric.metric_type == "steps",
                    )
                    .order_by(ActivityMetric.date.desc())
                    .limit(10)
                    .all()
                )

                print("Last 10 days:")
                for step in recent_steps:
                    print(
                        f"  🚶 {step.date.strftime('%Y-%m-%d')}: {step.value:,.0f} steps"
                    )

        print("=" * 70)
        print()
        print("✅ Step history imported successfully!")
        print("📊 Your walking patterns are now in the database")

        # Return success
        duration = time.time() - start_time
        return create_import_result(
            script_name="import_steps_history",
            success=True,
            inserted_count=inserted_count,
            skipped_count=skipped_count,
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Error: {str(e)}")
        return create_import_result(
            script_name="import_steps_history",
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


if __name__ == "__main__":
    main()
