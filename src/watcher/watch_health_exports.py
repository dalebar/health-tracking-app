#!/usr/bin/env python3
"""
Watch for health export files and trigger automatic import.

Monitors: /Users/daleb/Documents/health/
Target files:
  - export.zip (Apple Health)
  - File-Export-*.zip (MyFitnessPal nutrition data)

Triggers appropriate importer when file is detected and stable.
"""

import logging
import shutil
import sys
import tempfile
import threading
import time
import zipfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.importers.orchestrate_import import orchestrate_import
from src.watcher.notification_helper import send_notification

# Configure logging
LOG_FILE = Path(__file__).parent.parent.parent / "logs" / "import_history.log"
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
    """Handle file system events for health exports (Apple Health + MyFitnessPal)."""

    def __init__(self, watch_dir: Path):
        super().__init__()
        self.watch_dir = watch_dir
        self.last_modified: dict[Path, float] = {}  # Track file modification times
        self.debounce_seconds = 5  # Wait 5s after last modification
        self.import_in_progress = False  # Prevent concurrent imports
        self.pending_import: set[Path] = set()  # Track pending imports
        self._lock = threading.Lock()  # Synchronize access to shared state

    def _is_apple_health_export(self, filename: str) -> bool:
        """Check if file is an Apple Health export."""
        return filename == "export.zip"

    def _is_mfp_export(self, filename: str) -> bool:
        """Check if file is a MyFitnessPal export."""
        return filename.startswith("File-Export-") and filename.endswith(".zip")

    def _is_target_file(self, filename: str) -> bool:
        """Check if file should trigger an import."""
        return self._is_apple_health_export(filename) or self._is_mfp_export(filename)

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if self._is_target_file(file_path.name):
            logger.info(f"Detected new file: {file_path}")
            self._schedule_import(file_path)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        if self._is_target_file(file_path.name):
            logger.info(f"Detected modification: {file_path}")
            self._schedule_import(file_path)

    def _schedule_import(self, file_path: Path):
        """
        Schedule import after debounce period.

        Waits for file to be stable (no modifications for 5 seconds)
        before triggering import. Uses locking to prevent race conditions
        from multiple watchdog events.
        """
        with self._lock:
            # If import already pending for this file, just update timestamp
            if file_path in self.pending_import:
                self.last_modified[file_path] = time.time()
                return

            # Mark as pending to prevent duplicate scheduling
            self.pending_import.add(file_path)
            self.last_modified[file_path] = time.time()

        # Wait for file to stabilize (outside lock to not block other events)
        time.sleep(self.debounce_seconds)

        with self._lock:
            # Check if file was modified again during wait
            if file_path not in self.last_modified:
                self.pending_import.discard(file_path)
                return

            time_since_last_mod = time.time() - self.last_modified[file_path]

            if time_since_last_mod >= self.debounce_seconds:
                # File is stable, trigger import
                del self.last_modified[file_path]
                self.pending_import.discard(file_path)
                should_import = True
            else:
                # File was modified during wait, let the later event handle it
                self.pending_import.discard(file_path)
                should_import = False

        if should_import:
            self._trigger_import(file_path)

    def _trigger_import(self, zip_path: Path):
        """
        Trigger the appropriate import based on file type.

        Routes to Apple Health orchestrator or MyFitnessPal importer.
        """
        # Use lock to prevent race condition where two threads both see
        # import_in_progress=False and both start imports
        with self._lock:
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

            # Route to appropriate importer
            if self._is_apple_health_export(zip_path.name):
                self._import_apple_health(zip_path)
            elif self._is_mfp_export(zip_path.name):
                self._import_mfp(zip_path)

        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            send_notification(
                title="❌ Health Import Error",
                message=f"Import failed: {str(e)}. Check logs at {LOG_FILE}",
                sound="Basso",
            )

        finally:
            with self._lock:
                self.import_in_progress = False

    def _import_apple_health(self, zip_path: Path):
        """Import Apple Health export.zip using orchestrator."""
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

    def _import_mfp(self, zip_path: Path):
        """Import MyFitnessPal nutrition export."""
        from src.importers.myfitnesspal_importer import MyFitnessPalImporter
        from src.db.session import get_db_context

        temp_dir = None
        try:
            # Extract zip to temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix="mfp_import_"))
            logger.info(f"Extracting MFP export to: {temp_dir}")

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find Nutrition-Summary CSV file
            nutrition_files = list(temp_dir.rglob("Nutrition-Summary*.csv"))

            if not nutrition_files:
                raise ValueError("No Nutrition-Summary CSV found in zip")

            csv_path = nutrition_files[0]
            logger.info(f"Found nutrition file: {csv_path.name}")

            # Import using MyFitnessPalImporter
            start_time = time.time()
            with get_db_context() as db:
                importer = MyFitnessPalImporter(db)
                stats = importer.import_file(csv_path)

            duration = time.time() - start_time

            # Log results
            logger.info(f"MFP Import completed in {duration:.1f}s")
            logger.info(f"  Processed: {stats['processed']}")
            logger.info(f"  Inserted: {stats['inserted']}")
            logger.info(f"  Duplicates skipped: {stats['skipped_duplicates']}")
            logger.info(f"  Errors: {stats['errors']}")

            # Send notification
            if stats["errors"] == 0:
                send_notification(
                    title="✅ Nutrition Import Complete",
                    message=(
                        f"Imported {stats['inserted']} entries "
                        f"({stats['skipped_duplicates']} duplicates skipped). "
                        f"Took {duration:.0f}s."
                    ),
                    sound="Glass",
                )
            else:
                send_notification(
                    title="⚠️ Nutrition Import Completed with Errors",
                    message=(
                        f"Imported {stats['inserted']} entries, "
                        f"{stats['errors']} errors. Check logs."
                    ),
                    sound="Purr",
                )

        finally:
            # Clean up temp directory
            if temp_dir and temp_dir.exists():
                logger.info(f"Cleaning up: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)


def watch_for_exports(watch_dir: Path):
    """
    Start watching directory for health exports.

    Runs indefinitely until interrupted.
    """
    logger.info("=" * 70)
    logger.info("Starting Health Export Watcher")
    logger.info("=" * 70)
    logger.info(f"Watching: {watch_dir}")
    logger.info("Target files:")
    logger.info("  - export.zip (Apple Health)")
    logger.info("  - File-Export-*.zip (MyFitnessPal)")
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
