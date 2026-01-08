#!/usr/bin/env python3
"""
Import workout sessions from Apple Health.
"""

import time
from collections import Counter
from pathlib import Path

from src.db.models import User, Workout
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
    Import workouts from Apple Health export.

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        ImportResult with import statistics and status.
    """
    start_time = time.time()

    try:
        display_section_header("Apple Health Workouts Import")

        # Default path for backward compatibility (CLI usage)
        if export_path is None:
            export_path = Path(
                "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
            )

        if not export_path.exists():
            return create_import_result(
                script_name="import_workouts",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - start_time,
            )

        parser = AppleHealthParser()

        with get_db_context() as db:
            user = db.query(User).first()
            if not user:
                return create_import_result(
                    script_name="import_workouts",
                    success=False,
                    error_message="No user found. Run insert_initial_data.py first.",
                    duration_seconds=time.time() - start_time,
                )
            user_id = user.id

        # Parse workouts
        print("⏳ Parsing workout sessions (this may take 60-90 seconds)...")
        workouts_raw = parser.parse_workouts_from_file(export_path)
        print(f"✅ Found {len(workouts_raw)} workout sessions")

        if not workouts_raw:
            return create_import_result(
                script_name="import_workouts",
                success=True,
                inserted_count=0,
                skipped_count=0,
                duration_seconds=time.time() - start_time,
                error_message="No workout sessions found in export",
            )

        # DE-DUPLICATE by start_time (keep the one with most data)
        print("🔍 Checking for duplicates...")
        seen_times = {}
        workouts = []

        for workout in workouts_raw:
            start_time_value = workout["start_time"]

            if start_time_value not in seen_times:
                # First occurrence
                seen_times[start_time_value] = workout
                workouts.append(workout)
            else:
                # Duplicate found - keep the one with more data
                existing = seen_times[start_time_value]

                # Count non-None fields
                existing_fields = sum(1 for v in existing.values() if v is not None)
                new_fields = sum(1 for v in workout.values() if v is not None)

                if new_fields > existing_fields:
                    # New one has more data - replace it
                    workouts.remove(existing)
                    workouts.append(workout)
                    seen_times[start_time_value] = workout

        duplicates_removed = len(workouts_raw) - len(workouts)

        if duplicates_removed > 0:
            print(
                f"⚠️  Removed {duplicates_removed} duplicate workouts (kept most complete records)"
            )
        else:
            print("✅ No duplicates found")

        print()

        # Display date range
        if workouts:
            oldest = workouts[0]["start_time"]
            newest = workouts[-1]["end_time"]
            print(
                f"📅 Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}"
            )
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
        print("=" * 70)
        print("WORKOUT BREAKDOWN BY TYPE")
        print("=" * 70)

        # Count workout types
        workout_types = Counter(w["workout_type"] for w in workouts)

        for workout_type, count in workout_types.most_common():
            print(f"  🏃 {workout_type}: {count} sessions")

        print()
        print("=" * 70)
        print("RECENT WORKOUTS")
        print("=" * 70)

        with get_db_context() as db:
            user = db.query(User).first()
            if user:
                recent = (
                    db.query(Workout)
                    .filter(Workout.user_id == user.id)
                    .order_by(Workout.start_time.desc())
                    .limit(10)
                    .all()
                )

                print("Last 10 workouts:")
                for workout in recent:
                    print(
                        f"  🏋️  {workout.start_time.strftime('%Y-%m-%d')}: "
                        f"{workout.workout_type} - {workout.duration_minutes} min, "
                        f"{workout.total_energy_kcal} kcal"
                    )

        print("=" * 70)
        print()
        print("✅ Workouts imported successfully!")
        print("🏋️  Your training history is now tracked")

        # Return success
        duration = time.time() - start_time
        return create_import_result(
            script_name="import_workouts",
            success=True,
            inserted_count=inserted,
            skipped_count=skipped,
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Error: {str(e)}")
        return create_import_result(
            script_name="import_workouts",
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


if __name__ == "__main__":
    main()
