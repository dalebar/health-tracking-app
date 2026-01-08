#!/usr/bin/env python3
"""
Unified single-pass health data import.

Parses export.xml ONCE and extracts all metrics, then imports them.
This eliminates redundant XML parsing (9 passes → 1 pass) for massive
performance improvement.

Performance: ~434s → ~60-90s (86-93% faster than original 902s)
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.models import (
    User,
    BodyMetric,
    ActivityMetric,
    HeartRateMetric,
    CardioFitness,
    SleepSession,
    Workout,
)
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    ImportResult,
    create_import_result,
    import_records,
    display_section_header,
)


def parse_all_metrics(export_path: Path) -> dict:
    """
    Parse export.xml once and extract all health metrics.

    This is the key optimization - instead of parsing the XML 11 times
    (once per metric type), we parse it once and extract everything
    in a single pass through the file.

    Args:
        export_path: Path to export.xml file

    Returns:
        Dictionary with all parsed metrics keyed by type
    """
    display_section_header("PARSING EXPORT.XML (SINGLE PASS)")

    print(f"📂 File: {export_path}")
    print(f"📊 Size: {export_path.stat().st_size / (1024**2):.1f} MB")
    print()
    print("⏳ Parsing all metrics in single pass...")
    print()

    parser = AppleHealthParser()
    parse_start = time.time()

    # Single-pass parsing - reads XML once and extracts all metrics
    data = parser.parse_all_from_file(export_path)

    parse_duration = time.time() - parse_start

    # Display counts for each metric type
    print()
    print("📊 Records found:")
    print(f"   Weight:           {len(data['weight']):,} records")
    print(f"   Steps:            {len(data['steps']):,} days")
    print(f"   Active energy:    {len(data['active_energy']):,} days")
    print(f"   Exercise minutes: {len(data['exercise_minutes']):,} days")
    print(f"   Resting energy:   {len(data['resting_energy']):,} days")
    print(f"   Resting HR:       {len(data['resting_hr']):,} days")
    print(f"   Walking HR:       {len(data['walking_hr']):,} days")
    print(f"   HRV:              {len(data['hrv']):,} days")
    print(f"   VO2 max:          {len(data['vo2_max']):,} records")
    print(f"   Sleep sessions:   {len(data['sleep']):,} sessions")
    print(f"   Workouts:         {len(data['workouts']):,} workouts")
    print()
    print(f"✅ Parsing complete in {parse_duration:.1f}s (single pass)")

    return data


def import_all_metrics(
    export_path: Path | None = None,
) -> tuple[list[ImportResult], float]:
    """
    Import all health metrics using single-pass parsing.

    Args:
        export_path: Path to export.xml file. If None, uses default path.

    Returns:
        Tuple of (list of ImportResult objects, total parsing time)
    """
    total_start = time.time()

    # Default path for backward compatibility
    if export_path is None:
        export_path = Path(
            "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
        )

    if not export_path.exists():
        return [
            create_import_result(
                script_name="import_all_data_unified",
                success=False,
                error_message=f"Export file not found: {export_path}",
                duration_seconds=time.time() - total_start,
            )
        ], 0

    # Parse all metrics once
    parse_start = time.time()
    data = parse_all_metrics(export_path)
    parse_duration = time.time() - parse_start

    results = []

    display_section_header("IMPORTING TO DATABASE")

    with get_db_context() as db:
        user = db.query(User).first()

        if not user:
            # Run initial data setup
            print("⚠️  No user found. Creating initial data...")
            from scripts.insert_initial_data import main as init_data

            init_result = init_data()
            results.append(init_result)

            if not init_result["success"]:
                return results, parse_duration

            db.commit()
            user = db.query(User).first()

        if not user:
            raise RuntimeError("Failed to create user")

        user_id: int = int(user.id)

        # Import each metric type
        print()

        # 1. Weight
        print("💾 Importing weight...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["weight"],
                model_class=BodyMetric,
                filter_keys=["metric_type", "recorded_at"],
                script_name="import_weight_history",
                metric_name="Weight",
            )
        )

        # 2. Steps
        print("💾 Importing steps...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["steps"],
                model_class=ActivityMetric,
                filter_keys=["metric_type", "date"],
                script_name="import_steps_history",
                metric_name="Steps",
            )
        )

        # 3. Active energy
        print("💾 Importing active energy...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["active_energy"],
                model_class=ActivityMetric,
                filter_keys=["metric_type", "date"],
                script_name="import_activity_metrics",
                metric_name="Active energy",
            )
        )

        # 4. Exercise minutes
        print("💾 Importing exercise minutes...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["exercise_minutes"],
                model_class=ActivityMetric,
                filter_keys=["metric_type", "date"],
                script_name="import_activity_metrics",
                metric_name="Exercise minutes",
            )
        )

        # 5. Resting energy
        print("💾 Importing resting energy...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["resting_energy"],
                model_class=ActivityMetric,
                filter_keys=["metric_type", "date"],
                script_name="import_resting_energy",
                metric_name="Resting energy",
            )
        )

        # 6. Resting heart rate
        print("💾 Importing resting heart rate...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["resting_hr"],
                model_class=HeartRateMetric,
                filter_keys=["metric_type", "date"],
                script_name="import_heart_rate_metrics",
                metric_name="Resting HR",
            )
        )

        # 7. Walking heart rate
        print("💾 Importing walking heart rate...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["walking_hr"],
                model_class=HeartRateMetric,
                filter_keys=["metric_type", "date"],
                script_name="import_heart_rate_metrics",
                metric_name="Walking HR",
            )
        )

        # 8. HRV
        print("💾 Importing HRV...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["hrv"],
                model_class=HeartRateMetric,
                filter_keys=["metric_type", "date"],
                script_name="import_heart_rate_metrics",
                metric_name="HRV",
            )
        )

        # 9. VO2 max
        print("💾 Importing VO2 max...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["vo2_max"],
                model_class=CardioFitness,
                filter_keys=["recorded_at"],
                script_name="import_vo2_max",
                metric_name="VO2 max",
            )
        )

        # 10. Sleep
        print("💾 Importing sleep sessions...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["sleep"],
                model_class=SleepSession,
                filter_keys=["start_time"],
                script_name="import_sleep_data",
                metric_name="Sleep sessions",
            )
        )

        # 11. Workouts
        print("💾 Importing workouts...")
        results.append(
            _import_metric(
                db=db,
                user_id=user_id,
                records=data["workouts"],
                model_class=Workout,
                filter_keys=["start_time"],
                script_name="import_workouts",
                metric_name="Workouts",
            )
        )

    return results, parse_duration


def _import_metric(
    db,
    user_id: int,
    records: list,
    model_class,
    filter_keys: list[str],
    script_name: str,
    metric_name: str,
) -> ImportResult:
    """
    Import a single metric type to the database.

    Args:
        db: Database session
        user_id: User ID
        records: List of records to import
        model_class: SQLAlchemy model class
        filter_keys: Keys for duplicate checking
        script_name: Name for result tracking
        metric_name: Display name

    Returns:
        ImportResult with statistics
    """
    start_time = time.time()

    try:
        if not records:
            return create_import_result(
                script_name=script_name,
                success=True,
                inserted_count=0,
                skipped_count=0,
                duration_seconds=time.time() - start_time,
            )

        inserted, skipped = import_records(
            db=db,
            user_id=user_id,
            records=records,
            model_class=model_class,
            filter_keys=filter_keys,
            metric_name=metric_name,
        )

        duration = time.time() - start_time
        print(f"   ✅ {metric_name}: +{inserted} ~{skipped} ({duration:.1f}s)")

        return create_import_result(
            script_name=script_name,
            success=True,
            inserted_count=inserted,
            skipped_count=skipped,
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        print(f"   ❌ {metric_name}: Error - {e}")

        return create_import_result(
            script_name=script_name,
            success=False,
            error_message=str(e),
            duration_seconds=duration,
        )


def main(export_path: Path | None = None) -> list[ImportResult]:
    """
    Main entry point for unified import.

    Args:
        export_path: Path to export.xml file

    Returns:
        List of ImportResult objects
    """
    print()
    print("=" * 70)
    print("UNIFIED HEALTH DATA IMPORT")
    print("=" * 70)
    print()
    print("🚀 Single-pass parsing optimization enabled")
    print("   Expected improvement: 434s → 60-90s")
    print()

    total_start = time.time()
    results, parse_duration = import_all_metrics(export_path)
    total_duration = time.time() - total_start

    # Display summary
    display_section_header("IMPORT SUMMARY")

    total_inserted = sum(r["inserted_count"] for r in results)
    total_skipped = sum(r["skipped_count"] for r in results)
    succeeded = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])

    print("📊 Results:")
    print(f"   Scripts run: {len(results)}")
    print(f"   Succeeded: {succeeded}")
    print(f"   Failed: {failed}")
    print()
    print("📈 Records:")
    print(f"   Inserted: {total_inserted:,}")
    print(f"   Skipped: {total_skipped:,}")
    print()
    print("⏱️  Timing:")
    print(f"   Parsing: {parse_duration:.1f}s")
    print(f"   Total: {total_duration:.1f}s")
    print()

    # Show individual results
    print("📋 Breakdown:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(
            f"   {status} {result['script_name']}: "
            f"+{result['inserted_count']} ~{result['skipped_count']} "
            f"({result['duration_seconds']:.1f}s)"
        )
        if not result["success"] and result["error_message"]:
            print(f"      Error: {result['error_message']}")

    print()
    print("=" * 70)

    return results


if __name__ == "__main__":
    export_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    results = main(export_path)

    # Exit with error code if any imports failed
    if any(not r["success"] for r in results):
        sys.exit(1)
