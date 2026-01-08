#!/usr/bin/env python3
"""
Import VO2 max (cardio fitness) records from Apple Health.
"""

import time
from pathlib import Path

from src.db.models import User, CardioFitness
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
    Import VO2 max measurements from Apple Health export.

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        ImportResult with import statistics and status.
    """
    start_time = time.time()

    try:
        display_section_header("Apple Health VO2 Max Import")

        # Default path for backward compatibility (CLI usage)
        if export_path is None:
            export_path = Path(
                "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
            )

        if not export_path.exists():
            return create_import_result(
                script_name="import_vo2_max",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - start_time,
            )

        parser = AppleHealthParser()

        with get_db_context() as db:
            user = db.query(User).first()
            if not user:
                return create_import_result(
                    script_name="import_vo2_max",
                    success=False,
                    error_message="No user found. Run insert_initial_data.py first.",
                    duration_seconds=time.time() - start_time,
                )
            user_id = int(user.id)  # type: ignore[arg-type]

        # Parse VO2 max records
        print("⏳ Parsing VO2 max records (221 records)...")
        vo2_records = parser.parse_vo2_max_from_file(export_path)
        print(f"✅ Found {len(vo2_records)} VO2 max measurements")
        print()

        if not vo2_records:
            return create_import_result(
                script_name="import_vo2_max",
                success=True,
                inserted_count=0,
                skipped_count=0,
                duration_seconds=time.time() - start_time,
                error_message="No VO2 max records found in export",
            )

        # Import to database
        print("💾 Importing to database...")

        with get_db_context() as db:
            inserted, skipped = import_records(
                db=db,
                user_id=user_id,
                records=vo2_records,  # type: ignore[arg-type]
                model_class=CardioFitness,
                filter_keys=["recorded_at"],
                batch_size=50,
                metric_name="VO2 max",
            )
            display_import_summary("VO2 max", inserted, skipped)

        print()
        print("=" * 70)
        print("CARDIO FITNESS TREND")
        print("=" * 70)

        with get_db_context() as db:
            user = db.query(User).first()
            if user:
                all_vo2 = (
                    db.query(CardioFitness)
                    .filter(CardioFitness.user_id == user.id)
                    .order_by(CardioFitness.recorded_at)
                    .all()
                )

                if len(all_vo2) >= 2:
                    first = all_vo2[0]
                    last = all_vo2[-1]
                    change = float(last.vo2_max) - float(first.vo2_max)
                    sign = "+" if change > 0 else ""

                    print(
                        f"First recorded: {first.recorded_at.strftime('%Y-%m-%d')}: {first.vo2_max} mL/kg/min"
                    )
                    print(
                        f"Most recent:    {last.recorded_at.strftime('%Y-%m-%d')}: {last.vo2_max} mL/kg/min"
                    )
                    print(f"Total change:   {sign}{change:.1f} mL/kg/min")
                    print()

                    print("Last 10 measurements:")
                    for vo2 in all_vo2[-10:]:
                        print(
                            f"  💪 {vo2.recorded_at.strftime('%Y-%m-%d')}: {vo2.vo2_max} mL/kg/min"
                        )

        print("=" * 70)
        print()
        print("✅ VO2 max imported successfully!")
        print("💪 Your cardio fitness is now tracked")

        # Return success
        duration = time.time() - start_time
        return create_import_result(
            script_name="import_vo2_max",
            success=True,
            inserted_count=inserted,
            skipped_count=skipped,
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Error: {str(e)}")
        return create_import_result(
            script_name="import_vo2_max",
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


if __name__ == "__main__":
    main()
