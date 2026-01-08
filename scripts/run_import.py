#!/usr/bin/env python3
"""
Manually trigger health data import from export.zip.

Usage:
    ./scripts/run_import.py /path/to/export.zip
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.orchestrate_import import orchestrate_import


def main():
    """Run manual import with CLI argument."""

    if len(sys.argv) < 2:
        print("Usage: run_import.py <path_to_export.zip>")
        print()
        print("Example:")
        print("  python scripts/run_import.py ~/Documents/health/export.zip")
        sys.exit(1)

    zip_path = Path(sys.argv[1])

    if not zip_path.exists():
        print(f"❌ Error: File not found: {zip_path}")
        sys.exit(1)

    if not zip_path.suffix == ".zip":
        print(f"❌ Error: Expected .zip file, got: {zip_path.suffix}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("MANUAL HEALTH IMPORT")
    print("=" * 70)
    print(f"Import file: {zip_path}")
    print(f"File size: {zip_path.stat().st_size / (1024**2):.2f} MB")
    print("=" * 70)
    print()

    # Run orchestration
    result = orchestrate_import(zip_path)

    # Display summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    print(f"Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
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


if __name__ == "__main__":
    main()
