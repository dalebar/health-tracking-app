"""
MyFitnessPal CSV importer for nutrition data.

Imports Nutrition-Summary CSV exports from MyFitnessPal Premium.
"""

import csv
import logging
from datetime import datetime, date
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from src.db.models import NutritionLog, DailyNutritionSummary

logger = logging.getLogger(__name__)


class MyFitnessPalImporter:
    """Import nutrition data from MyFitnessPal CSV exports."""

    # Column mapping from CSV headers to our database fields
    COLUMN_MAP = {
        "Date": "date",
        "Meal": "meal",
        "Time": "time",
        "Calories": "calories",
        "Protein (g)": "protein_g",
        "Carbohydrates (g)": "carbohydrates_g",
        "Fat (g)": "fat_g",
        "Fiber": "fiber_g",
        "Sugar": "sugar_g",
        "Saturated Fat": "saturated_fat_g",
        "Polyunsaturated Fat": "polyunsaturated_fat_g",
        "Monounsaturated Fat": "monounsaturated_fat_g",
        "Trans Fat": "trans_fat_g",
        "Cholesterol": "cholesterol_mg",
        "Sodium (mg)": "sodium_mg",
        "Potassium": "potassium_mg",
        "Vitamin A": "vitamin_a_pct",
        "Vitamin C": "vitamin_c_pct",
        "Calcium": "calcium_pct",
        "Iron": "iron_pct",
        "Note": "note",
    }

    def __init__(self, db: Session):
        self.db = db
        self.stats = {
            "processed": 0,
            "inserted": 0,
            "skipped_duplicates": 0,
            "errors": 0,
        }
        self._affected_dates: set[date] = set()

    def import_file(self, file_path: Path) -> dict[str, int]:
        """
        Import a MyFitnessPal Nutrition-Summary CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            Import statistics dict
        """
        logger.info(f"Importing MFP nutrition data from {file_path}")

        if not file_path.name.startswith("Nutrition-Summary"):
            logger.info(f"Skipping non-nutrition file: {file_path.name}")
            return self.stats

        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                self.stats["processed"] += 1
                try:
                    self._process_row(row, file_path.name)
                except Exception as e:
                    logger.error(f"Error processing row {self.stats['processed']}: {e}")
                    self.stats["errors"] += 1

        # Commit logs first
        self.db.commit()

        # After importing logs, update daily summaries for affected dates
        self._update_daily_summaries()

        self.db.commit()
        logger.info(f"Import complete: {self.stats}")
        return self.stats

    def _process_row(self, row: dict[str, str], source_file: str) -> None:
        """Process a single CSV row."""
        # Parse date
        date_str = row.get("Date", "").strip()
        if not date_str:
            return

        date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
        self._affected_dates.add(date_val)

        # Parse time (can be empty) - format: "7:15 AM" or "6:50 PM"
        time_val = None
        time_str = row.get("Time", "").strip()
        if time_str:
            try:
                time_val = datetime.strptime(time_str, "%I:%M %p").time()
            except ValueError:
                pass  # Keep as None if parsing fails

        # Build record
        record: dict[str, Any] = {
            "user_id": 1,
            "date": date_val,
            "meal": row.get("Meal", "").strip(),
            "time": time_val,
            "source": "myfitnesspal",
            "source_file": source_file,
        }

        # Map numeric fields
        for csv_col, db_col in self.COLUMN_MAP.items():
            if csv_col in ["Date", "Meal", "Time", "Note"]:
                continue
            value = row.get(csv_col, "").strip()
            if value:
                try:
                    record[db_col] = Decimal(value)
                except InvalidOperation:
                    record[db_col] = None
            else:
                record[db_col] = None

        # Handle note
        record["note"] = row.get("Note", "").strip() or None

        # Upsert with conflict handling
        stmt = insert(NutritionLog).values(**record)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["user_id", "date", "meal", "time", "calories", "protein_g"]
        )
        result = self.db.execute(stmt)

        if result.rowcount > 0:  # type: ignore[attr-defined]
            self.stats["inserted"] += 1
        else:
            self.stats["skipped_duplicates"] += 1

    def _update_daily_summaries(self) -> None:
        """Recalculate daily nutrition summaries for affected dates."""
        if not self._affected_dates:
            return

        logger.info(f"Updating daily summaries for {len(self._affected_dates)} dates")

        for summary_date in self._affected_dates:
            # Query aggregates for this date
            logs = (
                self.db.query(NutritionLog)
                .filter(
                    NutritionLog.user_id == 1,
                    NutritionLog.date == summary_date,
                )
                .all()
            )

            if not logs:
                continue

            # Calculate totals
            total_calories = sum(
                float(log.calories) for log in logs if log.calories is not None
            )
            total_protein = sum(
                float(log.protein_g) for log in logs if log.protein_g is not None
            )
            total_carbs = sum(
                float(log.carbohydrates_g)
                for log in logs
                if log.carbohydrates_g is not None
            )
            total_fat = sum(float(log.fat_g) for log in logs if log.fat_g is not None)
            total_fiber = sum(
                float(log.fiber_g) for log in logs if log.fiber_g is not None
            )
            total_sugar = sum(
                float(log.sugar_g) for log in logs if log.sugar_g is not None
            )
            total_sodium = sum(
                float(log.sodium_mg) for log in logs if log.sodium_mg is not None
            )

            # Calculate meal breakdown
            breakfast_cals = sum(
                float(log.calories)
                for log in logs
                if log.meal == "Breakfast" and log.calories is not None
            )
            lunch_cals = sum(
                float(log.calories)
                for log in logs
                if log.meal == "Lunch" and log.calories is not None
            )
            dinner_cals = sum(
                float(log.calories)
                for log in logs
                if log.meal == "Dinner" and log.calories is not None
            )
            snacks_cals = sum(
                float(log.calories)
                for log in logs
                if log.meal == "Snacks" and log.calories is not None
            )

            # Count unique meals and total entries
            unique_meals = len(set(log.meal for log in logs))
            entry_count = len(logs)

            # Upsert summary
            summary_data = {
                "user_id": 1,
                "date": summary_date,
                "total_calories": Decimal(str(total_calories)),
                "total_protein_g": Decimal(str(total_protein)),
                "total_carbohydrates_g": Decimal(str(total_carbs)),
                "total_fat_g": Decimal(str(total_fat)),
                "total_fiber_g": Decimal(str(total_fiber)),
                "total_sugar_g": Decimal(str(total_sugar)),
                "total_sodium_mg": Decimal(str(total_sodium)),
                "breakfast_calories": Decimal(str(breakfast_cals)),
                "lunch_calories": Decimal(str(lunch_cals)),
                "dinner_calories": Decimal(str(dinner_cals)),
                "snacks_calories": Decimal(str(snacks_cals)),
                "meal_count": unique_meals,
                "entry_count": entry_count,
                "updated_at": func.now(),
            }

            stmt = insert(DailyNutritionSummary).values(**summary_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id", "date"],
                set_={
                    "total_calories": summary_data["total_calories"],
                    "total_protein_g": summary_data["total_protein_g"],
                    "total_carbohydrates_g": summary_data["total_carbohydrates_g"],
                    "total_fat_g": summary_data["total_fat_g"],
                    "total_fiber_g": summary_data["total_fiber_g"],
                    "total_sugar_g": summary_data["total_sugar_g"],
                    "total_sodium_mg": summary_data["total_sodium_mg"],
                    "breakfast_calories": summary_data["breakfast_calories"],
                    "lunch_calories": summary_data["lunch_calories"],
                    "dinner_calories": summary_data["dinner_calories"],
                    "snacks_calories": summary_data["snacks_calories"],
                    "meal_count": summary_data["meal_count"],
                    "entry_count": summary_data["entry_count"],
                    "updated_at": func.now(),
                },
            )
            self.db.execute(stmt)


def import_mfp_file(file_path: Path) -> dict[str, int]:
    """
    Convenience function to import a single MFP file.

    Args:
        file_path: Path to the CSV file

    Returns:
        Import statistics dict
    """
    from src.db.session import get_db_context

    with get_db_context() as db:
        importer = MyFitnessPalImporter(db)
        return importer.import_file(file_path)
