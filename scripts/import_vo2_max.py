#!/usr/bin/env python3
"""
Import VO2 max (cardio fitness) records from Apple Health.
"""

from pathlib import Path

from src.db.models import User, CardioFitness
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser


def main():
    """Import VO2 max measurements from Apple Health export."""

    print("=" * 70)
    print("Apple Health VO2 Max Import")
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

    # Parse VO2 max records
    print("⏳ Parsing VO2 max records (221 records)...")
    vo2_records = parser.parse_vo2_max_from_file(export_path)
    print(f"✅ Found {len(vo2_records)} VO2 max measurements")
    print()

    # Import to database
    print("💾 Importing to database...")

    with get_db_context() as db:
        inserted = 0
        skipped = 0

        for record in vo2_records:
            existing = (
                db.query(CardioFitness)
                .filter(
                    CardioFitness.user_id == user_id,
                    CardioFitness.recorded_at == record["recorded_at"],
                )
                .first()
            )

            if existing:
                skipped += 1
                continue

            fitness = CardioFitness(
                user_id=user_id,
                vo2_max=record["vo2_max"],
                recorded_at=record["recorded_at"],
                source=record["source"],
            )
            db.add(fitness)
            inserted += 1

            if inserted % 50 == 0:
                db.commit()
                print(f"  VO2 max: {inserted} records...")

        db.commit()

        print(f"✅ VO2 max: {inserted} inserted, {skipped} skipped")

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
