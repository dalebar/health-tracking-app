"""
Apple Health XML parser for extracting health metrics.
"""

from collections import defaultdict
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import TypedDict

from defusedxml import ElementTree as ET


class MetricResult(TypedDict):
    """Type definition for metric results."""

    metric_type: str
    value: Decimal
    unit: str
    date: date
    recorded_at: datetime
    source: str


class WeightRecord(TypedDict):
    """Type definition for weight records (timestamp-based, not aggregated by date)."""

    metric_type: str
    value: Decimal
    unit: str
    recorded_at: datetime
    source: str


class VO2MaxRecord(TypedDict):
    """Type definition for VO2 max records."""

    vo2_max: Decimal
    recorded_at: datetime
    source: str


class AppleHealthParser:
    """Parser for Apple Health export XML files."""

    def parse_weight_record(self, xml_string: str) -> WeightRecord:
        """
        Parse a single weight record from XML string.

        Args:
            xml_string: XML string containing a Record element

        Returns:
            Dictionary with parsed weight data

        Raises:
            ValueError: If required attributes are missing
        """
        root = ET.fromstring(xml_string.strip())

        # Extract required attributes with validation
        value_str = root.get("value")
        unit = root.get("unit")
        source = root.get("sourceName")
        date_str = root.get("startDate")

        # Validate required fields
        if not value_str:
            raise ValueError("Missing required attribute: value")
        if not unit:
            raise ValueError("Missing required attribute: unit")
        if not date_str:
            raise ValueError("Missing required attribute: startDate")

        # Parse values (now type checker knows they're not None)
        value = Decimal(value_str)
        recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z").replace(
            tzinfo=None
        )

        return {
            "metric_type": "weight",
            "value": value,
            "unit": unit,
            "recorded_at": recorded_at,
            "source": source or "unknown",  # source is optional
        }

    def parse_weight_from_file(self, file_path: str | Path) -> list[WeightRecord]:
        """
        Parse all weight records from Apple Health export XML file.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of weight records sorted by date (oldest first)
        """
        # Parse XML file in chunks to handle large files efficiently
        results: list[WeightRecord] = []

        # Use iterparse to avoid loading entire 1.7GB file into memory
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKQuantityTypeIdentifierBodyMass"
            ):
                try:
                    value_str = elem.get("value")
                    unit = elem.get("unit")
                    source = elem.get("sourceName")
                    date_str = elem.get("startDate")

                    if not value_str or not unit or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(
                        date_str, "%Y-%m-%d %H:%M:%S %z"
                    ).replace(tzinfo=None)

                    results.append(
                        {
                            "metric_type": "weight",
                            "value": value,
                            "unit": unit,
                            "recorded_at": recorded_at,
                            "source": source or "apple_health",
                        }
                    )
                except (ValueError, TypeError):
                    # Skip malformed records
                    continue
                finally:
                    # Clear element to free memory
                    elem.clear()

        # Sort by date (oldest first)
        results.sort(key=lambda x: x["recorded_at"])

        return results

    def parse_step_records(self, xml_string: str) -> list[MetricResult]:
        """
        Parse and aggregate step records by date.

        Args:
            xml_string: XML string containing Record elements

        Returns:
            List of aggregated daily step totals
        """
        root = ET.fromstring(xml_string.strip())

        # Aggregate steps by date
        daily_steps: defaultdict[date, Decimal] = defaultdict(Decimal)

        for record in root.findall("Record"):
            # Only process step count records
            if record.get("type") != "HKQuantityTypeIdentifierStepCount":
                continue

            value_str = record.get("value")
            unit = record.get("unit")
            date_str = record.get("startDate")

            # Skip records missing required fields
            if not value_str or not unit or not date_str:
                continue

            value = Decimal(value_str)
            recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
            record_date = recorded_at.date()

            daily_steps[record_date] += value

        # Convert to list of results
        results: list[MetricResult] = []
        for record_date, total_steps in daily_steps.items():
            results.append(
                {
                    "metric_type": "steps",
                    "value": total_steps,
                    "unit": "count",
                    "date": record_date,
                    "recorded_at": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        return results

    def parse_steps_from_file(self, file_path: str | Path) -> list[MetricResult]:
        """
        Parse all step records from Apple Health export and aggregate by date.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of daily step totals sorted by date (oldest first)
        """
        # Aggregate steps by date
        daily_steps: defaultdict[date, Decimal] = defaultdict(Decimal)

        # Use iterparse for memory efficiency
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKQuantityTypeIdentifierStepCount"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
                    record_date = recorded_at.date()

                    # Aggregate by date
                    daily_steps[record_date] += value

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        # Convert to list and sort
        results: list[MetricResult] = []
        for record_date, total_steps in daily_steps.items():
            results.append(
                {
                    "metric_type": "steps",
                    "value": total_steps,
                    "unit": "count",
                    "date": record_date,
                    "recorded_at": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        results.sort(key=lambda x: x["date"])
        return results

    def parse_active_energy_from_file(
        self, file_path: str | Path
    ) -> list[MetricResult]:
        """
        Parse active energy records and aggregate by date.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of daily active energy totals (kcal)
        """
        daily_energy: defaultdict[date, Decimal] = defaultdict(Decimal)
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKQuantityTypeIdentifierActiveEnergyBurned"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
                    record_date = recorded_at.date()

                    daily_energy[record_date] += value

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        results: list[MetricResult] = []
        for record_date, total_energy in daily_energy.items():
            results.append(
                {
                    "metric_type": "active_energy",
                    "value": total_energy,
                    "unit": "kcal",
                    "date": record_date,
                    "recorded_at": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        results.sort(key=lambda x: x["date"])
        return results

    def parse_exercise_minutes_from_file(
        self, file_path: str | Path
    ) -> list[MetricResult]:
        """
        Parse exercise time records and aggregate by date.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of daily exercise minutes totals
        """
        daily_exercise: defaultdict[date, Decimal] = defaultdict(Decimal)
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKQuantityTypeIdentifierAppleExerciseTime"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
                    record_date = recorded_at.date()

                    daily_exercise[record_date] += value

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        results: list[MetricResult] = []
        for record_date, total_minutes in daily_exercise.items():
            results.append(
                {
                    "metric_type": "exercise_minutes",
                    "value": total_minutes,
                    "unit": "min",
                    "date": record_date,
                    "recorded_at": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        results.sort(key=lambda x: x["date"])
        return results

    def parse_resting_heart_rate_from_file(
        self, file_path: str | Path
    ) -> list[MetricResult]:
        """
        Parse resting heart rate records and aggregate by date.

        Multiple readings per day are averaged.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of daily resting heart rate averages
        """
        # Aggregate resting HR by date (can have multiple readings per day)
        daily_hr: defaultdict[date, list[Decimal]] = defaultdict(list)
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKQuantityTypeIdentifierRestingHeartRate"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
                    record_date = recorded_at.date()

                    daily_hr[record_date].append(value)

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        # Calculate daily averages
        results: list[MetricResult] = []
        for record_date, values in daily_hr.items():
            avg_hr = Decimal(sum(values) / len(values))
            results.append(
                {
                    "metric_type": "resting_hr",
                    "value": avg_hr,
                    "unit": "bpm",
                    "date": record_date,
                    "recorded_at": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        results.sort(key=lambda x: x["date"])
        return results

    def parse_walking_heart_rate_from_file(
        self, file_path: str | Path
    ) -> list[MetricResult]:
        """
        Parse walking heart rate records and aggregate by date.

        Multiple readings per day are averaged.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of daily walking heart rate averages
        """
        # Aggregate walking HR by date (can have multiple readings per day)
        daily_hr: defaultdict[date, list[Decimal]] = defaultdict(list)
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type")
                == "HKQuantityTypeIdentifierWalkingHeartRateAverage"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
                    record_date = recorded_at.date()

                    daily_hr[record_date].append(value)

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        # Calculate daily averages
        results: list[MetricResult] = []
        for record_date, values in daily_hr.items():
            avg_hr = Decimal(sum(values) / len(values))
            results.append(
                {
                    "metric_type": "walking_hr",
                    "value": avg_hr,
                    "unit": "bpm",
                    "date": record_date,
                    "recorded_at": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        results.sort(key=lambda x: x["date"])
        return results

    def parse_hrv_from_file(self, file_path: str | Path) -> list[MetricResult]:
        """
        Parse Heart Rate Variability (HRV) records and aggregate by date.

        HRV can have multiple readings per day. We take the MAXIMUM value as this
        represents peak cardiovascular recovery capacity (typically during deep sleep).
        Maximum HRV is a better indicator of heart health than average, as it shows
        what your heart can achieve when fully rested.
        ...
        Returns:
        List of daily maximum HRV values (in milliseconds)
        """
        # Aggregate HRV by date (multiple readings per day)
        daily_hrv: defaultdict[date, list[Decimal]] = defaultdict(list)
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type")
                == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
                    record_date = recorded_at.date()

                    daily_hrv[record_date].append(value)

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        # Calculate daily averages
        results: list[MetricResult] = []
        for record_date, values in daily_hrv.items():
            avg_hrv = max(values)
            results.append(
                {
                    "metric_type": "hrv",
                    "value": avg_hrv,
                    "unit": "ms",
                    "date": record_date,
                    "recorded_at": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        results.sort(key=lambda x: x["date"])
        return results

    def parse_vo2_max_from_file(self, file_path: str | Path) -> list[VO2MaxRecord]:
        """
        Parse VO2 max (cardio fitness) records.

        VO2 max is calculated periodically by Apple Watch and represents
        cardiovascular fitness level (ml/kg/min). Higher values = better fitness.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of VO2 max measurements
        """
        results: list[VO2MaxRecord] = []
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKQuantityTypeIdentifierVO2Max"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")
                    source = elem.get("sourceName")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(
                        date_str, "%Y-%m-%d %H:%M:%S %z"
                    ).replace(tzinfo=None)

                    results.append(
                        {
                            "vo2_max": value,
                            "recorded_at": recorded_at,
                            "source": source or "apple_health",
                        }
                    )

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        # Sort by date (oldest first)
        results.sort(key=lambda x: x["recorded_at"])
        return results
