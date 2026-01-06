#!/usr/bin/env python3
"""
Import VO2 max (cardio fitness) records from Apple Health.
"""

from pathlib import Path

from src.db.models import User, CardioFitness
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    import_records,
    display_import_summary,
    display_section_header,
)


def main():
    """Import VO2 max measurements from Apple Health export."""

    display_section_header("Apple Health VO2 Max Import")

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

    # Parse VO2 max records
    print("⏳ Parsing VO2 max records (221 records)...")
    vo2_records = parser.parse_vo2_max_from_file(export_path)
    print(f"✅ Found {len(vo2_records)} VO2 max measurements")
    print()

    # Import to database
    print("💾 Importing to database...")

    with get_db_context() as db:
        inserted, skipped = import_records(
            db=db,
            user_id=user_id,
            records=vo2_records,
            model_class=CardioFitness,
            filter_keys=["recorded_at"],
            batch_size=50,
            metric_name="VO2 max",
        )
        display_import_summary("VO2 max", inserted, skipped)

    print()
    print("=" * 70)
    print("VO2 MAX TREND SUMMARY")
    print("=" * 70)

    with get_db_context() as db:
        user = db.query(User).first()
        if not user:
            return

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
                f"First recorded:  {first.recorded_at.strftime('%Y-%m-%d')}: {first.vo2_max} ml/kg/min"
            )
            print(
                f"Most recent:     {last.recorded_at.strftime('%Y-%m-%d')}: {last.vo2_max} ml/kg/min"
            )
            print(f"Total change:    {sign}{change:.1f} ml/kg/min")
            print()

            print("Last 10 measurements:")
            for vo2 in all_vo2[-10:]:
                print(
                    f"  💪 {vo2.recorded_at.strftime('%Y-%m-%d')}: {vo2.vo2_max} ml/kg/min"
                )

    print("=" * 70)
    print()
    print("✅ VO2 max imported successfully!")
    print("📈 Your cardiovascular fitness history is now tracked")


if __name__ == "__main__":
    main()
