#!/usr/bin/env python3
"""
Import workout sessions from Apple Health.
"""

from collections import Counter
from pathlib import Path

from src.db.models import User, Workout
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    import_records,
    display_import_summary,
    display_section_header,
)


def main():
    """Import workouts from Apple Health export."""

    display_section_header("Apple Health Workouts Import")

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

    # Parse workouts
    print("⏳ Parsing workout sessions (this may take 60-90 seconds)...")
    workouts_raw = parser.parse_workouts_from_file(export_path)
    print(f"✅ Found {len(workouts_raw)} workout sessions")

    # DE-DUPLICATE by start_time (keep the one with most data)
    print("🔍 Checking for duplicates...")
    seen_times = {}
    workouts = []

    for workout in workouts_raw:
        start_time = workout["start_time"]

        if start_time not in seen_times:
            # First occurrence
            seen_times[start_time] = workout
            workouts.append(workout)
        else:
            # Duplicate found - keep the one with more data
            existing = seen_times[start_time]

            # Count non-None fields
            existing_fields = sum(1 for v in existing.values() if v is not None)
            new_fields = sum(1 for v in workout.values() if v is not None)

            if new_fields > existing_fields:
                # New one has more data - replace it
                workouts.remove(existing)
                workouts.append(workout)
                seen_times[start_time] = workout

    duplicates_removed = len(workouts_raw) - len(workouts)

    if duplicates_removed > 0:
        print(
            f"⚠️  Removed {duplicates_removed} duplicate workouts (kept most complete records)"
        )
    else:
        print("✅ No duplicates found")

    print(f"📊 Final workout count: {len(workouts)}")
    print()

    if not workouts:
        print("No workouts found in export.")
        return

    # Display date range
    oldest = workouts[0].get("start_time")
    newest = workouts[-1].get("end_time")
    if not oldest or not newest:
        print("❌ Missing start_time or end_time in workout data")
        return
    print(
        f"📅 Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
    )
    print()

    # Show workout type breakdown
    workout_types = Counter(w["workout_type"] for w in workouts)
    print("Workout Types:")
    for wtype, count in workout_types.most_common():
        print(f"  🏃 {wtype}: {count}")
    print()

    # Import to database
    print("💾 Importing to database...")

    with get_db_context() as db:
        inserted, skipped = import_records(
            db=db,
            user_id=user_id,
            records=workouts,
            model_class=Workout,
            filter_keys=["start_time"],
            batch_size=50,
            metric_name="Workouts",
        )
        display_import_summary("Workouts", inserted, skipped)
        print()

    # Display summary
    print("=" * 70)
    print("RECENT WORKOUTS SUMMARY")
    print("=" * 70)

    with get_db_context() as db:
        user = db.query(User).first()
        if not user:
            return

        recent_workouts = (
            db.query(Workout)
            .filter(Workout.user_id == user.id)
            .order_by(Workout.start_time.desc())
            .limit(10)
            .all()
        )

        print("Last 10 workouts:")
        for workout in recent_workouts:
            duration_hours = float(workout.duration_minutes) / 60

            parts = [
                f"  {workout.start_time.strftime('%Y-%m-%d')}:",
                f"{workout.workout_type}",
                f"{duration_hours:.1f}h",
            ]

            if workout.total_energy_kcal:
                parts.append(f"{workout.total_energy_kcal:.0f} kcal")

            if workout.avg_heart_rate_bpm:
                parts.append(
                    f"HR avg {workout.avg_heart_rate_bpm} "
                    f"(max {workout.max_heart_rate_bpm})"
                )

            if workout.distance_km:
                parts.append(f"{workout.distance_km:.1f} km")

            print(" | ".join(parts))

    print("=" * 70)
    print()
    print("✅ Workouts imported successfully!")
    print("🥊 Your training history is now tracked")


if __name__ == "__main__":
    main()
