#!/usr/bin/env python3
"""
Import step count history from Apple Health export to database.
"""

from pathlib import Path

from src.db.models import User, ActivityMetric
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser


def main():
    """Import step counts from Apple Health export."""

    print("=" * 70)
    print("Apple Health Steps Import")
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

    print("⏳ Parsing step records (aggregating 69K+ records by date)...")
    print("   This may take 60-90 seconds...")
    parser = AppleHealthParser()
    step_records = parser.parse_steps_from_file(export_path)

    print(f"✅ Aggregated to {len(step_records)} daily totals")
    print()

    if not step_records:
        print("No step records found in export.")
        return

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
            print("❌ No user found. Run insert_initial_data.py first.")
            return

        user_id = user.id

        inserted_count = 0
        skipped_count = 0

        for record in step_records:
            # Check if record already exists
            existing = (
                db.query(ActivityMetric)
                .filter(
                    ActivityMetric.user_id == user_id,
                    ActivityMetric.metric_type == "steps",
                    ActivityMetric.date == record["date"],
                )
                .first()
            )

            if existing:
                skipped_count += 1
                continue

            # Insert new record
            metric = ActivityMetric(
                user_id=user_id,
                metric_type=record["metric_type"],
                value=record["value"],
                unit=record["unit"],
                date=record["date"],
                recorded_at=record["recorded_at"],
                source=record["source"],
            )
            db.add(metric)
            inserted_count += 1

            # Commit in batches
            if inserted_count % 100 == 0:
                db.commit()
                print(f"  Inserted {inserted_count} records...")

        db.commit()

    print()
    print(f"✅ Inserted: {inserted_count} new records")
    print(f"⏭️  Skipped: {skipped_count} existing records")
    print()

    # Display recent activity
    print("=" * 70)
    print("RECENT STEP ACTIVITY")
    print("=" * 70)

    with get_db_context() as db:
        user = db.query(User).first()

        if not user:
            return

        recent_steps = (
            db.query(ActivityMetric)
            .filter(
                ActivityMetric.user_id == user.id, ActivityMetric.metric_type == "steps"
            )
            .order_by(ActivityMetric.date.desc())
            .limit(10)
            .all()
        )

        print("Last 10 days:")
        for step in recent_steps:
            print(f"  🚶 {step.date.strftime('%Y-%m-%d')}: {step.value:,.0f} steps")

    print("=" * 70)
    print()
    print("✅ Step history imported successfully!")
    print("📊 Your walking patterns are now in the database")


if __name__ == "__main__":
    main()
