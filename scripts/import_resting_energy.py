#!/usr/bin/env python3
"""
Import resting energy (basal metabolic rate) from Apple Health.
"""

from pathlib import Path

from src.db.models import User, ActivityMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    import_records,
    display_import_summary,
    display_section_header,
)


def main():
    """Import resting energy from Apple Health export."""

    display_section_header("Apple Health Resting Energy Import")

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

    # Parse Resting Energy
    print("⏳ Parsing resting energy (1.1M+ records → daily totals)...")
    print("   This may take 60-90 seconds...")
    resting_records = parser.parse_resting_energy_from_file(export_path)
    print(f"✅ Aggregated to {len(resting_records)} daily totals")
    print()

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
        if not user:
            return

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


if __name__ == "__main__":
    main()
