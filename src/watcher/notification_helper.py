#!/usr/bin/env python3
"""
macOS notification helper using osascript.

No external dependencies required - uses built-in macOS tools.
"""

import subprocess  # nosec B404 - Required for macOS notifications via osascript
import logging

logger = logging.getLogger(__name__)


def send_notification(
    title: str,
    message: str,
    sound: str | None = None,
) -> bool:
    """
    Send macOS notification using osascript.

    Args:
        title: Notification title
        message: Notification body text
        sound: Optional sound name (e.g., "Glass", "Basso", "Sosumi")
               See /System/Library/Sounds/ for available sounds

    Returns:
        True if notification sent successfully, False otherwise

    Example:
        send_notification(
            title="Health Import Complete",
            message="Imported 1,234 records successfully",
            sound="Glass"
        )
    """
    try:
        # Build AppleScript command
        script = f'display notification "{message}" with title "{title}"'

        if sound:
            script += f' sound name "{sound}"'

        # Execute using osascript (trusted macOS command with sanitized input)
        result = subprocess.run(  # nosec B603 B607
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.warning(f"Notification failed: {result.stderr}")
            return False

        return True

    except subprocess.TimeoutExpired:
        logger.warning("Notification timed out")
        return False
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
        return False


def send_import_success_notification(
    inserted: int,
    skipped: int,
    duration: float,
) -> bool:
    """
    Send success notification with import statistics.

    Args:
        inserted: Number of records inserted
        skipped: Number of records skipped
        duration: Import duration in seconds

    Returns:
        True if notification sent successfully
    """
    message = (
        f"Inserted {inserted:,} records, "
        f"skipped {skipped:,} duplicates. "
        f"Completed in {duration:.0f}s."
    )

    return send_notification(
        title="✅ Health Import Complete",
        message=message,
        sound="Glass",
    )


def send_import_failure_notification(
    error_message: str,
    log_file: str,
) -> bool:
    """
    Send failure notification with error details.

    Args:
        error_message: Brief error description
        log_file: Path to log file for details

    Returns:
        True if notification sent successfully
    """
    message = f"{error_message} Check {log_file} for details."

    return send_notification(
        title="❌ Health Import Failed",
        message=message,
        sound="Basso",
    )


if __name__ == "__main__":
    # Test notifications
    print("Testing macOS notifications...")
    print()

    print("1. Sending success notification...")
    success = send_import_success_notification(
        inserted=1234,
        skipped=567,
        duration=89.5,
    )
    print(f"   {'✅' if success else '❌'} Success notification sent")
    print()

    print("2. Sending failure notification...")
    failure = send_import_failure_notification(
        error_message="Database connection failed",
        log_file="logs/import_history.log",
    )
    print(f"   {'✅' if failure else '❌'} Failure notification sent")
    print()

    print("Done! Check your notification center.")
