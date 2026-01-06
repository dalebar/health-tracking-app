#!/usr/bin/env python3
"""
Import sleep session data from Apple Health.
"""

from pathlib import Path

from src.db.models import User, SleepSession
from src.db.session import get_db_context
from src.parsers.apple_health_parser import AppleHealthParser
from src.utils.import_helpers import (
    import_records,
    display_import_summary,
    display_section_header,
)


def main():
    """Import sleep sessions from Apple Health export."""

    display_section_header("Apple Health Sleep Data Import")

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

    # Parse sleep sessions
    print("⏳ Parsing sleep sessions (this may take 60-90 seconds)...")
    sleep_sessions = parser.parse_sleep_from_file(export_path)
    print(f"✅ Found {len(sleep_sessions)} sleep sessions")
    print()

    if not sleep_sessions:
        print("No sleep sessions found in export.")
        return

    # Display date range
    oldest = sleep_sessions[0]["start_time"]
    newest = sleep_sessions[-1]["end_time"]
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
            records=sleep_sessions,
            model_class=SleepSession,
            filter_keys=["start_time"],
            batch_size=50,
            metric_name="Sleep sessions",
        )
        display_import_summary("Sleep sessions", inserted, skipped)
        print()

    # Display summary
    print("=" * 70)
    print("SLEEP SUMMARY")
    print("=" * 70)

    with get_db_context() as db:
        user = db.query(User).first()
        if not user:
            return

        recent_sessions = (
            db.query(SleepSession)
            .filter(SleepSession.user_id == user.id)
            .order_by(SleepSession.start_time.desc())
            .limit(10)
            .all()
        )

        print("Last 10 sleep sessions:")
        for session in recent_sessions:
            total_hours = session.total_duration_minutes / 60
            deep_hours = (
                session.deep_minutes / 60 if session.deep_minutes is not None else 0
            )
            rem_hours = (
                session.rem_minutes / 60 if session.rem_minutes is not None else 0
            )
            core_hours = (
                session.core_minutes / 60 if session.core_minutes is not None else 0
            )
            awake_hours = (
                session.awake_minutes / 60 if session.awake_minutes is not None else 0
            )

            print(
                f"  😴 {session.end_time.strftime('%Y-%m-%d')}: "
                f"{total_hours:.1f}h total "
                f"(Deep: {deep_hours:.1f}h, REM: {rem_hours:.1f}h, "
                f"Core: {core_hours:.1f}h, Awake: {awake_hours:.1f}h)"
            )

    print("=" * 70)
    print()
    print("✅ Sleep data imported successfully!")
    print("😴 Your sleep patterns are now tracked")


if __name__ == "__main__":
    main()
