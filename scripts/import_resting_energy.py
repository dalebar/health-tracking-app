#!/usr/bin/env python3
"""
Import resting energy (basal metabolic rate) from Apple Health.
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
    Import resting energy from Apple Health export.

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        ImportResult with import statistics and status.
    """
    start_time = time.time()

    try:
        display_section_header("Apple Health Resting Energy Import")

        # Default path for backward compatibility (CLI usage)
        if export_path is None:
            export_path = Path(
                "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
            )

        if not export_path.exists():
            return create_import_result(
                script_name="import_resting_energy",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - start_time,
            )

        parser = AppleHealthParser()

        with get_db_context() as db:
            user = db.query(User).first()
            if not user:
                return create_import_result(
                    script_name="import_resting_energy",
                    success=False,
                    error_message="No user found. Run insert_initial_data.py first.",
                    duration_seconds=time.time() - start_time,
                )
            user_id = user.id

        # Parse Resting Energy
        print("⏳ Parsing resting energy (1.1M+ records → daily totals)...")
        print("   This may take 60-90 seconds...")
        resting_records = parser.parse_resting_energy_from_file(export_path)
        print(f"✅ Aggregated to {len(resting_records)} daily totals")
        print()

        if not resting_records:
            return create_import_result(
                script_name="import_resting_energy",
                success=True,
                inserted_count=0,
                skipped_count=0,
                duration_seconds=time.time() - start_time,
                error_message="No resting energy records found in export",
            )

        # Import to database
        print("💾 Importing to database...")

        with get_db_context() as db:
            inserted, skipped = import_records(
                db=db,
                user_id=user_id,
                records=resting_records,
                model_class=ActivityMetric,
                filter_keys=["metric_type", "date"],
                metric_name="Resting Energy",
            )
            display_import_summary("Resting Energy", inserted, skipped)

        print()
        print("=" * 70)
        print("RECENT RESTING ENERGY")
        print("=" * 70)

        with get_db_context() as db:
            user = db.query(User).first()
            if user:
                recent = (
                    db.query(ActivityMetric)
                    .filter(
                        ActivityMetric.user_id == user.id,
                        ActivityMetric.metric_type == "resting_energy",
                    )
                    .order_by(ActivityMetric.date.desc())
                    .limit(10)
                    .all()
                )

                print("Last 10 days:")
                for metric in recent:
                    print(
                        f"  🔥 {metric.date.strftime('%Y-%m-%d')}: "
                        f"{metric.value:,.0f} kcal (BMR)"
                    )

        print("=" * 70)
        print()
        print("✅ Resting energy imported successfully!")
        print("🔥 Your daily BMR is now tracked for accurate TDEE calculation")

        # Return success
        duration = time.time() - start_time
        return create_import_result(
            script_name="import_resting_energy",
            success=True,
            inserted_count=inserted,
            skipped_count=skipped,
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Error: {str(e)}")
        return create_import_result(
            script_name="import_resting_energy",
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


if __name__ == "__main__":
    main()
