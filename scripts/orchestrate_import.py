#!/usr/bin/env python3
"""
Orchestrate the full Apple Health import process.

This script:
1. Extracts export.zip to temporary directory
2. Runs all import scripts in sequence
3. Aggregates results
4. Cleans up temporary files
5. Returns comprehensive import summary
"""

import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import TypedDict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.import_helpers import ImportResult


class OrchestrationResult(TypedDict):
    """Overall result from orchestrating all imports."""

    success: bool
    total_duration_seconds: float
    scripts_run: int
    scripts_succeeded: int
    scripts_failed: int
    total_inserted: int
    total_skipped: int
    results: list[ImportResult]
    error_message: str | None


def extract_export_zip(zip_path: Path) -> Path:
    """
    Extract export.zip to temporary directory.

    Args:
        zip_path: Path to export.zip file

    Returns:
        Path to extracted export.xml file

    Raises:
        ValueError: If zip is invalid or export.xml not found
    """
    # Create temp directory that persists for session
    temp_dir = Path(tempfile.mkdtemp(prefix="health_import_"))

    try:
        # Extract zip
        print(f"📦 Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # Find export.xml (usually in apple_health_export/export.xml)
        export_xml_candidates = list(temp_dir.rglob("export.xml"))

        if not export_xml_candidates:
            raise ValueError(f"No export.xml found in {zip_path}")

        export_xml = export_xml_candidates[0]
        print(f"✅ Extracted to: {export_xml.parent}")
        print(f"📊 File size: {export_xml.stat().st_size / (1024**3):.2f} GB")
        print()

        return export_xml

    except Exception:
        # Clean up on failure
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def run_import_scripts(export_xml_path: Path) -> list[ImportResult]:
    """
    Run all import scripts in sequence.

    Args:
        export_xml_path: Path to extracted export.xml

    Returns:
        List of ImportResult from each script

    Note:
        Scripts are run in dependency order:
        1. insert_initial_data (must run first - creates user)
        2. All other imports (order doesn't matter after user exists)
    """
    results: list[ImportResult] = []

    # Import script modules
    import scripts.insert_initial_data as insert_initial
    import scripts.import_weight_history as weight
    import scripts.import_steps_history as steps
    import scripts.import_activity_metrics as activity
    import scripts.import_resting_energy as resting
    import scripts.import_heart_rate_metrics as heart
    import scripts.import_vo2_max as vo2
    import scripts.import_sleep_data as sleep_data
    import scripts.import_workouts as workouts

    # Script execution order: user creation first, then all imports
    scripts: list[tuple[str, Any, bool]] = [
        ("insert_initial_data", insert_initial.main, False),  # No export_path needed
        ("import_weight_history", weight.main, True),
        ("import_steps_history", steps.main, True),
        ("import_activity_metrics", activity.main, True),
        ("import_resting_energy", resting.main, True),
        ("import_heart_rate_metrics", heart.main, True),
        ("import_vo2_max", vo2.main, True),
        ("import_sleep_data", sleep_data.main, True),
        ("import_workouts", workouts.main, True),
    ]

    for script_name, script_func, needs_path in scripts:
        print(f"\n{'='*70}")
        print(f"Running: {script_name}")
        print(f"{'='*70}\n")

        try:
            if needs_path:
                result = script_func(export_path=export_xml_path)
            else:
                result = script_func()

            results.append(result)

            status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
            print(f"\n{status}: {script_name}")
            print(f"  Inserted: {result['inserted_count']}")
            print(f"  Skipped: {result['skipped_count']}")
            print(f"  Duration: {result['duration_seconds']:.2f}s")

            if not result["success"]:
                print(f"  Error: {result['error_message']}")

            # Show per-metric breakdown for multi-metric scripts
            if result.get("metrics"):
                print("  Metrics breakdown:")
                for metric in result["metrics"]:
                    print(
                        f"    - {metric['name']}: "
                        f"+{metric['inserted']} ~{metric['skipped']}"
                    )

        except Exception as e:
            # Catch any unexpected errors
            error_result: ImportResult = {
                "script_name": script_name,
                "success": False,
                "inserted_count": 0,
                "skipped_count": 0,
                "duration_seconds": 0.0,
                "error_message": f"Unexpected error: {str(e)}",
                "metrics": [],
            }
            results.append(error_result)
            print(f"\n❌ FAILED: {script_name} - {str(e)}")

    return results


def orchestrate_import(zip_path: Path) -> OrchestrationResult:
    """
    Main orchestration function: extract, import, cleanup.

    Args:
        zip_path: Path to export.zip file

    Returns:
        OrchestrationResult with comprehensive import summary
    """
    start_time = time.time()
    temp_dir: Path | None = None

    try:
        print("\n" + "=" * 70)
        print("HEALTH DATA IMPORT ORCHESTRATION")
        print("=" * 70)
        print(f"Source: {zip_path}")
        print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        # Extract export
        export_xml_path = extract_export_zip(zip_path)
        temp_dir = export_xml_path.parent.parent  # Save for cleanup

        # Run all imports
        print("Starting import sequence...")
        print()
        results = run_import_scripts(export_xml_path)

        # Aggregate statistics
        total_inserted = sum(r["inserted_count"] for r in results)
        total_skipped = sum(r["skipped_count"] for r in results)
        scripts_succeeded = sum(1 for r in results if r["success"])
        scripts_failed = len(results) - scripts_succeeded

        overall_success = scripts_failed == 0

        return {
            "success": overall_success,
            "total_duration_seconds": time.time() - start_time,
            "scripts_run": len(results),
            "scripts_succeeded": scripts_succeeded,
            "scripts_failed": scripts_failed,
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
            "results": results,
            "error_message": (
                None if overall_success else f"{scripts_failed} script(s) failed"
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "total_duration_seconds": time.time() - start_time,
            "scripts_run": 0,
            "scripts_succeeded": 0,
            "scripts_failed": 0,
            "total_inserted": 0,
            "total_skipped": 0,
            "results": [],
            "error_message": f"Orchestration failed: {str(e)}",
        }

    finally:
        # Clean up temp directory
        if temp_dir and temp_dir.exists():
            print(f"\n🧹 Cleaning up temporary files: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: orchestrate_import.py <path_to_export.zip>")
        print()
        print("Example:")
        print("  python scripts/orchestrate_import.py ~/Documents/health/export.zip")
        sys.exit(1)

    zip_path = Path(sys.argv[1])

    if not zip_path.exists():
        print(f"❌ Error: File not found: {zip_path}")
        sys.exit(1)

    if not zip_path.suffix == ".zip":
        print(f"❌ Error: Expected .zip file, got: {zip_path.suffix}")
        sys.exit(1)

    # Run orchestration
    result = orchestrate_import(zip_path)

    # Display summary
    print("\n" + "=" * 70)
    print("ORCHESTRATION SUMMARY")
    print("=" * 70)
    print(f"Overall: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
    print(f"Duration: {result['total_duration_seconds']:.1f}s")
    print()
    print(f"Scripts run: {result['scripts_run']}")
    print(f"  Succeeded: {result['scripts_succeeded']}")
    print(f"  Failed: {result['scripts_failed']}")
    print()
    print("Records:")
    print(f"  Inserted: {result['total_inserted']:,}")
    print(f"  Skipped: {result['total_skipped']:,}")

    if result["scripts_failed"] > 0:
        print()
        print("Failed scripts:")
        for script_result in result["results"]:
            if not script_result["success"]:
                print(f"  - {script_result['script_name']}")
                print(f"    Error: {script_result['error_message']}")

    print("=" * 70)
    print()

    sys.exit(0 if result["success"] else 1)
