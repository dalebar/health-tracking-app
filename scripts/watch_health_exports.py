#!/usr/bin/env python3
"""
Watch for Apple Health export files and trigger automatic import.

Monitors: /Users/daleb/Documents/health/
Target file: export.zip
Triggers: orchestrate_import.py when file is detected and stable
"""

import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.orchestrate_import import orchestrate_import
from scripts.notification_helper import send_notification

# Configure logging
LOG_FILE = Path(__file__).parent.parent / "logs" / "import_history.log"
LOG_FILE.parent.mkdir(exist_ok=True)

# Setup logging with rotation
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class HealthExportHandler(FileSystemEventHandler):
    """Handle file system events for Apple Health exports."""

    def __init__(self, watch_dir: Path, target_filename: str = "export.zip"):
        super().__init__()
        self.watch_dir = watch_dir
        self.target_filename = target_filename
        self.last_modified: dict[Path, float] = {}  # Track file modification times
        self.debounce_seconds = 5  # Wait 5s after last modification
        self.import_in_progress = False  # Prevent concurrent imports

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if file_path.name == self.target_filename:
            logger.info(f"Detected new file: {file_path}")
            self._schedule_import(file_path)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if file_path.name == self.target_filename:
            logger.info(f"Detected modification: {file_path}")
            self._schedule_import(file_path)

    def _schedule_import(self, file_path: Path):
        """
        Schedule import after debounce period.

        Waits for file to be stable (no modifications for 5 seconds)
        before triggering import.
        """
        self.last_modified[file_path] = time.time()

        # Wait for file to stabilize
        time.sleep(self.debounce_seconds)

        # Check if file was modified again during wait
        if file_path in self.last_modified:
            time_since_last_mod = time.time() - self.last_modified[file_path]

            if time_since_last_mod >= self.debounce_seconds:
                # File is stable, trigger import
                del self.last_modified[file_path]
                self._trigger_import(file_path)

    def _trigger_import(self, zip_path: Path):
        """
        Trigger the import orchestration.

        Runs orchestrate_import, logs results, sends notification.
        """
        if self.import_in_progress:
            logger.warning("Import already in progress, skipping")
            send_notification(
                title="Health Import Skipped",
                message="Another import is already running",
                sound="Tink",
            )
            return

        self.import_in_progress = True

        try:
            logger.info(f"Starting import for: {zip_path}")
            logger.info(f"File size: {zip_path.stat().st_size / (1024**2):.1f} MB")

            # Run orchestration
            result = orchestrate_import(zip_path)

            # Log results
            logger.info(f"Import completed - Success: {result['success']}")
            logger.info(f"Scripts run: {result['scripts_run']}")
            logger.info(f"Succeeded: {result['scripts_succeeded']}")
            logger.info(f"Failed: {result['scripts_failed']}")
            logger.info(f"Inserted: {result['total_inserted']}")
            logger.info(f"Skipped: {result['total_skipped']}")
            logger.info(f"Duration: {result['total_duration_seconds']:.1f}s")

            # Log individual script results
            for script_result in result["results"]:
                status = "OK" if script_result["success"] else "FAIL"
                logger.info(
                    f"  [{status}] {script_result['script_name']}: "
                    f"+{script_result['inserted_count']} "
                    f"~{script_result['skipped_count']} "
                    f"({script_result['duration_seconds']:.1f}s)"
                )
                if not script_result["success"]:
                    logger.error(f"    Error: {script_result['error_message']}")

            # Send notification
            if result["success"]:
                send_notification(
                    title="✅ Health Import Complete",
                    message=(
                        f"Successfully imported {result['total_inserted']:,} records "
                        f"({result['scripts_succeeded']}/{result['scripts_run']} scripts). "
                        f"Took {result['total_duration_seconds']:.0f}s."
                    ),
                    sound="Glass",
                )
            else:
                send_notification(
                    title="❌ Health Import Failed",
                    message=(
                        f"{result['scripts_failed']} script(s) failed. "
                        f"Check logs at {LOG_FILE}"
                    ),
                    sound="Basso",
                )

        except Exception as e:
            logger.error(f"Import orchestration failed: {e}", exc_info=True)
            send_notification(
                title="❌ Health Import Error",
                message=f"Import failed: {str(e)}. Check logs at {LOG_FILE}",
                sound="Basso",
            )

        finally:
            self.import_in_progress = False


def watch_for_exports(watch_dir: Path):
    """
    Start watching directory for health exports.

    Runs indefinitely until interrupted.
    """
    logger.info("=" * 70)
    logger.info("Starting Health Export Watcher")
    logger.info("=" * 70)
    logger.info(f"Watching: {watch_dir}")
    logger.info("Target file: export.zip")
    logger.info(f"Logging to: {LOG_FILE}")
    logger.info("=" * 70)

    if not watch_dir.exists():
        logger.error(f"Watch directory does not exist: {watch_dir}")
        raise ValueError(f"Directory not found: {watch_dir}")

    event_handler = HealthExportHandler(watch_dir)
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=False)
    observer.start()

    logger.info("✅ Watcher started successfully")
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()

    observer.join()
    logger.info("Watcher stopped")


if __name__ == "__main__":
    watch_dir = Path("/Users/daleb/Documents/health")
    watch_for_exports(watch_dir)
