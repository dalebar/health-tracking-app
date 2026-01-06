#!/usr/bin/env python3
"""
Delete existing HRV records so we can re-import with maximum values.
"""

from src.db.models import HeartRateMetric
from src.db.session import get_db_context


def main():
    """Delete all HRV records from database."""

    print("=" * 70)
    print("Delete HRV Records")
    print("=" * 70)
    print()

    with get_db_context() as db:
        # Count existing
        count = (
            db.query(HeartRateMetric)
            .filter(HeartRateMetric.metric_type == "hrv")
            .count()
        )

        print(f"Found {count} existing HRV records")

        if count == 0:
            print("No HRV records to delete")
            return

        # Delete
        db.query(HeartRateMetric).filter(HeartRateMetric.metric_type == "hrv").delete()

        db.commit()

        print(f"✅ Deleted {count} HRV records")
        print()
        print("Ready to re-import with maximum values!")


if __name__ == "__main__":
    main()
