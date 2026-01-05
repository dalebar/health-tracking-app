#!/usr/bin/env python3
"""
Import weight history from Apple Health export to database.
"""

from pathlib import Path

from src.db.models import User, BodyMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser


def main():
    """Import weight measurements from Apple Health export."""

    print("=" * 70)
    print("Apple Health Weight Import")
    print("=" * 70)
    print()

    export_path = Path(
        "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
    )

    if not export_path.exists():
        print(f"❌ Export file not found: {export_path}")
        return

    print(f"📂 Reading: {export_path}")
    print(f"📊 File size: {export_path.stat().st_size / (1024**3):.2f} GB")
    print()

    print("⏳ Parsing weight records (this may take 30-60 seconds)...")
    parser = AppleHealthParser()
    weight_records = parser.parse_weight_from_file(export_path)

    print(f"✅ Found {len(weight_records)} weight measurements")
    print()

    if not weight_records:
        print("No weight records found in export.")
        return

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
            print("❌ No user found. Run insert_initial_data.py first.")
            return

        user_id = user.id  # Store ID before session closes

        inserted_count = 0
        skipped_count = 0

        for record in weight_records:
            existing = (
                db.query(BodyMetric)
                .filter(
                    BodyMetric.user_id == user_id,
                    BodyMetric.metric_type == "weight",
                    BodyMetric.recorded_at == record["recorded_at"],
                )
                .first()
            )

            if existing:
                skipped_count += 1
                continue

            metric = BodyMetric(
                user_id=user_id,
                metric_type=record["metric_type"],
                value=record["value"],
                unit=record["unit"],
                recorded_at=record["recorded_at"],
                source=record["source"],
            )
            db.add(metric)
            inserted_count += 1

            if inserted_count % 100 == 0:
                db.commit()
                print(f"  Inserted {inserted_count} records...")

        db.commit()

    print()
    print(f"✅ Inserted: {inserted_count} new records")
    print(f"⏭️  Skipped: {skipped_count} existing records")
    print()

    print("=" * 70)
    print("WEIGHT TREND SUMMARY")
    print("=" * 70)

    with get_db_context() as db:
        user = db.query(User).first()  # Query user again in new session

        if not user:
            print("❌ No user found for weight trend summary.")
            return

        all_weights = (
            db.query(BodyMetric)
            .filter(BodyMetric.user_id == user.id, BodyMetric.metric_type == "weight")
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


if __name__ == "__main__":
    main()
