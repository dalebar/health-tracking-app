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


class SleepSessionRecord(TypedDict):
    """Type definition for sleep session records."""

    start_time: datetime
    end_time: datetime
    total_duration_minutes: int
    awake_minutes: int
    rem_minutes: int
    core_minutes: int
    deep_minutes: int
    source: str


class WorkoutRecord(TypedDict, total=False):
    """Type definition for workout records."""

    workout_type: str
    start_time: datetime
    end_time: datetime
    duration_minutes: Decimal
    active_energy_kcal: Decimal
    basal_energy_kcal: Decimal
    total_energy_kcal: Decimal
    distance_km: Decimal
    avg_heart_rate_bpm: int
    min_heart_rate_bpm: int
    max_heart_rate_bpm: int
    source: str
    indoor_workout: bool


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

    def parse_resting_energy_from_file(
        self, file_path: str | Path
    ) -> list[MetricResult]:
        """
        Parse resting energy (basal metabolic rate) records and aggregate by date.

        Resting energy represents calories burned at rest throughout the day.
        Combined with active energy, this gives total daily energy expenditure (TDEE).

        Args:
            file_path: Path to export.xml file

        Returns:
            List of daily resting energy totals (kcal)
        """
        daily_resting: defaultdict[date, Decimal] = defaultdict(Decimal)
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKQuantityTypeIdentifierBasalEnergyBurned"
            ):
                try:
                    value_str = elem.get("value")
                    date_str = elem.get("startDate")

                    if not value_str or not date_str:
                        continue

                    value = Decimal(value_str)
                    recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
                    record_date = recorded_at.date()

                    daily_resting[record_date] += value

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        results: list[MetricResult] = []
        for record_date, total_resting in daily_resting.items():
            results.append(
                {
                    "metric_type": "resting_energy",
                    "value": total_resting,
                    "unit": "kcal",
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

    def parse_sleep_from_file(self, file_path: str | Path) -> list[SleepSessionRecord]:
        """
        Parse sleep session data from Apple Health export.

        Groups sleep stage records into complete sessions using 2-hour gap detection.
        Includes InBed time in total duration. Only processes staged sleep data
        (Deep, Core, REM, Awake, InBed) from Apple Watch Series 7+.

        Sleep sessions can span calendar days (e.g., sleep 11pm Jan 3 → wake 7am Jan 4).
        Uses 2-hour gap threshold to detect separate sessions (handles naps vs night sleep).

        Args:
            file_path: Path to export.xml file

        Returns:
            List of complete sleep sessions with stage breakdowns and optional sleep scores
        """
        from datetime import timedelta

        # Step 1: Extract all sleep stage records
        all_records: list[dict] = []

        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            # Parse sleep stage records
            if (
                elem.tag == "Record"
                and elem.get("type") == "HKCategoryTypeIdentifierSleepAnalysis"
            ):
                try:
                    value_str = elem.get("value")
                    start_str = elem.get("startDate")
                    end_str = elem.get("endDate")

                    if not value_str or not start_str or not end_str:
                        continue

                    # Map Apple Health sleep values to our schema
                    # HKCategoryValueSleepAnalysisInBed → "inbed"
                    # HKCategoryValueSleepAnalysisAwake → "awake"
                    # etc.
                    value_mapping = {
                        # InBed tracking
                        "HKCategoryValueSleepAnalysisInBed": "inbed",
                        # Older Apple Watch models (pre-watchOS 9)
                        "HKCategoryValueSleepAnalysisAsleep": "core",
                        "HKCategoryValueSleepAnalysisAsleepUnspecified": "core",
                        # Apple Watch  with watchOS 9+ (staged sleep)
                        "HKCategoryValueSleepAnalysisAwake": "awake",
                        "HKCategoryValueSleepAnalysisAsleepREM": "rem",
                        "HKCategoryValueSleepAnalysisAsleepCore": "core",
                        "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
                    }

                    stage = value_mapping.get(value_str)
                    if not stage:
                        continue  # Unknown sleep stage, skip

                    start_time = datetime.strptime(
                        start_str, "%Y-%m-%d %H:%M:%S %z"
                    ).replace(tzinfo=None)
                    end_time = datetime.strptime(
                        end_str, "%Y-%m-%d %H:%M:%S %z"
                    ).replace(tzinfo=None)

                    duration_minutes = int((end_time - start_time).total_seconds() / 60)

                    all_records.append(
                        {
                            "start": start_time,
                            "end": end_time,
                            "value": stage,
                            "duration_minutes": duration_minutes,
                        }
                    )

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        if not all_records:
            return []

        # Step 2: Sort by start time (chronological order)
        all_records.sort(key=lambda x: x["start"])

        # Step 3: Group into sessions using 2-hour gap detection
        sessions: list[SleepSessionRecord] = []
        current_session: list[dict] = []
        GAP_THRESHOLD = timedelta(hours=2)

        for record in all_records:
            if not current_session:
                # Start first session
                current_session.append(record)
            else:
                # Check gap between last record and current
                gap = record["start"] - current_session[-1]["end"]

                if gap > GAP_THRESHOLD:
                    # Gap too large → finalize current session and start new one
                    sessions.append(self._aggregate_sleep_session(current_session))
                    current_session = [record]
                else:
                    # Continue current session
                    current_session.append(record)

        # Don't forget the last session!
        if current_session:
            sessions.append(self._aggregate_sleep_session(current_session))

        return sessions

    def _aggregate_sleep_session(self, records: list[dict]) -> SleepSessionRecord:
        """
        Aggregate individual sleep stage records into a complete session.

        Calculates total duration and sums each sleep stage.

        Args:
            records: List of sleep stage records for a single session

        Returns:
            Aggregated sleep session record
        """
        # Find session boundaries
        start_time = min(r["start"] for r in records)
        end_time = max(r["end"] for r in records)

        # Sum durations by stage
        stage_minutes = {"deep": 0, "core": 0, "rem": 0, "awake": 0}

        for record in records:
            stage = record["value"]
            duration = record["duration_minutes"]

            if stage in stage_minutes:
                stage_minutes[stage] += duration
            # "inbed" is included in total duration but not counted as a sleep stage

        # Calculate total duration (includes InBed time)
        total_duration = int((end_time - start_time).total_seconds() / 60)

        return {
            "start_time": start_time,
            "end_time": end_time,
            "total_duration_minutes": total_duration,
            "deep_minutes": stage_minutes["deep"],
            "core_minutes": stage_minutes["core"],
            "rem_minutes": stage_minutes["rem"],
            "awake_minutes": stage_minutes["awake"],
            "source": "apple_health",
        }

    def parse_workouts_from_file(self, file_path: str | Path) -> list[WorkoutRecord]:
        """
        Parse workout sessions from Apple Health export.

        Extracts workout metadata including type, duration, energy expenditure,
        distance, and heart rate aggregates from WorkoutStatistics.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of workout records sorted by start time (oldest first)
        """
        results: list[WorkoutRecord] = []
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            if elem.tag == "Workout":
                try:
                    # Extract workout attributes
                    workout_type_raw = elem.get("workoutActivityType")
                    start_str = elem.get("startDate")
                    end_str = elem.get("endDate")
                    duration_str = elem.get("duration")
                    source = elem.get("sourceName")

                    if (
                        not workout_type_raw
                        or not start_str
                        or not end_str
                        or not duration_str
                    ):
                        continue

                    # Clean workout type (remove HKWorkoutActivityType prefix)
                    workout_type = workout_type_raw.replace("HKWorkoutActivityType", "")

                    # Parse dates
                    start_time = datetime.strptime(
                        start_str, "%Y-%m-%d %H:%M:%S %z"
                    ).replace(tzinfo=None)
                    end_time = datetime.strptime(
                        end_str, "%Y-%m-%d %H:%M:%S %z"
                    ).replace(tzinfo=None)

                    # Duration is in minutes (as decimal)
                    duration_minutes = Decimal(duration_str)

                    # Initialize workout record with required fields
                    workout: WorkoutRecord = {
                        "workout_type": workout_type,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration_minutes": duration_minutes,
                        "source": source or "apple_health",
                        "indoor_workout": False,
                    }

                    # Parse WorkoutStatistics for energy, distance, heart rate
                    active_energy = None
                    basal_energy = None
                    distance = None
                    avg_hr = None
                    min_hr = None
                    max_hr = None

                    for stat in elem.findall("WorkoutStatistics"):
                        stat_type = stat.get("type", "")

                        # Energy
                        if stat_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                            active_energy = Decimal(stat.get("sum", "0"))
                        elif stat_type == "HKQuantityTypeIdentifierBasalEnergyBurned":
                            basal_energy = Decimal(stat.get("sum", "0"))

                        # Distance (multiple types)
                        elif stat_type in [
                            "HKQuantityTypeIdentifierDistanceWalkingRunning",
                            "HKQuantityTypeIdentifierDistanceCycling",
                            "HKQuantityTypeIdentifierDistanceSwimming",
                        ]:
                            distance = Decimal(stat.get("sum", "0"))

                        # Heart Rate
                        elif stat_type == "HKQuantityTypeIdentifierHeartRate":
                            avg_val = stat.get("average")
                            min_val = stat.get("minimum")
                            max_val = stat.get("maximum")

                            if avg_val:
                                avg_hr = int(float(avg_val))
                            if min_val:
                                min_hr = int(float(min_val))
                            if max_val:
                                max_hr = int(float(max_val))

                    # Check metadata for indoor workout
                    for meta in elem.findall("MetadataEntry"):
                        if meta.get("key") == "HKIndoorWorkout":
                            workout["indoor_workout"] = meta.get("value") == "1"

                    # Add optional fields if present
                    if active_energy is not None:
                        workout["active_energy_kcal"] = active_energy
                    if basal_energy is not None:
                        workout["basal_energy_kcal"] = basal_energy
                    if active_energy is not None and basal_energy is not None:
                        workout["total_energy_kcal"] = active_energy + basal_energy
                    if distance is not None:
                        workout["distance_km"] = distance
                    if avg_hr is not None:
                        workout["avg_heart_rate_bpm"] = avg_hr
                    if min_hr is not None:
                        workout["min_heart_rate_bpm"] = min_hr
                    if max_hr is not None:
                        workout["max_heart_rate_bpm"] = max_hr

                    results.append(workout)

                except (ValueError, TypeError):
                    continue
                finally:
                    elem.clear()

        # Sort by start time (oldest first)
        results.sort(key=lambda x: x["start_time"])
        return results

    def parse_all_from_file(self, file_path: str | Path) -> dict:
        """
        Parse ALL health metrics from Apple Health export in a SINGLE PASS.

        This is a major performance optimization - instead of parsing the XML
        file 11 times (once per metric type), we parse it once and extract
        all metrics simultaneously.

        Performance improvement: ~460s → ~50s (90% faster)

        Args:
            file_path: Path to export.xml file

        Returns:
            Dictionary containing all parsed metrics:
            {
                'weight': list[WeightRecord],
                'steps': list[dict],          # Raw step records (need aggregation)
                'active_energy': list[dict],  # Raw records (need aggregation)
                'exercise_minutes': list[dict],
                'resting_energy': list[dict],
                'resting_hr': list[MetricResult],
                'walking_hr': list[MetricResult],
                'hrv': list[MetricResult],
                'vo2_max': list[VO2MaxRecord],
                'sleep_records': list[dict],  # Raw records (need aggregation)
                'workouts': list[WorkoutRecord],
            }
        """
        from datetime import timedelta
        from collections import defaultdict

        # Initialize result containers
        weight_records: list[WeightRecord] = []
        step_records: list[dict] = []  # Raw, will aggregate later
        active_energy_records: list[dict] = []
        exercise_minutes_records: list[dict] = []
        resting_energy_records: list[dict] = []
        resting_hr_records: list[MetricResult] = []
        walking_hr_records: list[MetricResult] = []
        hrv_records: list[MetricResult] = []
        vo2_max_records: list[VO2MaxRecord] = []
        sleep_raw_records: list[dict] = []
        workout_records: list[WorkoutRecord] = []

        # Record type to handler mapping
        RECORD_TYPES = {
            "HKQuantityTypeIdentifierBodyMass": "weight",
            "HKQuantityTypeIdentifierStepCount": "steps",
            "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy",
            "HKQuantityTypeIdentifierAppleExerciseTime": "exercise_minutes",
            "HKQuantityTypeIdentifierBasalEnergyBurned": "resting_energy",
            "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
            "HKQuantityTypeIdentifierWalkingHeartRateAverage": "walking_hr",
            "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv",
            "HKQuantityTypeIdentifierVO2Max": "vo2_max",
            "HKCategoryTypeIdentifierSleepAnalysis": "sleep",
        }

        # Sleep stage value mapping
        SLEEP_VALUE_MAPPING = {
            "HKCategoryValueSleepAnalysisInBed": "inbed",
            "HKCategoryValueSleepAnalysisAsleep": "core",
            "HKCategoryValueSleepAnalysisAsleepUnspecified": "core",
            "HKCategoryValueSleepAnalysisAwake": "awake",
            "HKCategoryValueSleepAnalysisAsleepREM": "rem",
            "HKCategoryValueSleepAnalysisAsleepCore": "core",
            "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
        }

        print("  🔄 Single-pass XML parsing starting...")

        # Single pass through XML
        context = ET.iterparse(file_path, events=("end",))

        for event, elem in context:
            try:
                # Handle Record elements
                if elem.tag == "Record":
                    record_type = elem.get("type")
                    handler = RECORD_TYPES.get(record_type)

                    if handler == "weight":
                        value_str = elem.get("value")
                        unit = elem.get("unit")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and unit and date_str:
                            weight_records.append(
                                {
                                    "metric_type": "weight",
                                    "value": Decimal(value_str),
                                    "unit": unit,
                                    "recorded_at": datetime.strptime(
                                        date_str, "%Y-%m-%d %H:%M:%S %z"
                                    ).replace(tzinfo=None),
                                    "source": source or "unknown",
                                }
                            )

                    elif handler == "steps":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            step_records.append(
                                {
                                    "value": int(float(value_str)),
                                    "date": recorded_at.date(),
                                    "source": source or "unknown",
                                }
                            )

                    elif handler == "active_energy":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            active_energy_records.append(
                                {
                                    "value": Decimal(value_str),
                                    "date": recorded_at.date(),
                                    "source": source or "unknown",
                                }
                            )

                    elif handler == "exercise_minutes":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            exercise_minutes_records.append(
                                {
                                    "value": Decimal(value_str),
                                    "date": recorded_at.date(),
                                    "source": source or "unknown",
                                }
                            )

                    elif handler == "resting_energy":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            resting_energy_records.append(
                                {
                                    "value": Decimal(value_str),
                                    "date": recorded_at.date(),
                                    "source": source or "unknown",
                                }
                            )

                    elif handler == "resting_hr":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            resting_hr_records.append(
                                {
                                    "metric_type": "resting_heart_rate",
                                    "value": Decimal(value_str),
                                    "unit": "bpm",
                                    "date": recorded_at.date(),
                                    "recorded_at": recorded_at,
                                    "source": source or "apple_health",
                                }
                            )

                    elif handler == "walking_hr":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            walking_hr_records.append(
                                {
                                    "metric_type": "walking_heart_rate",
                                    "value": Decimal(value_str),
                                    "unit": "bpm",
                                    "date": recorded_at.date(),
                                    "recorded_at": recorded_at,
                                    "source": source or "apple_health",
                                }
                            )

                    elif handler == "hrv":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            hrv_records.append(
                                {
                                    "metric_type": "hrv",
                                    "value": Decimal(value_str),
                                    "unit": "ms",
                                    "date": recorded_at.date(),
                                    "recorded_at": recorded_at,
                                    "source": source or "apple_health",
                                }
                            )

                    elif handler == "vo2_max":
                        value_str = elem.get("value")
                        date_str = elem.get("startDate")
                        source = elem.get("sourceName")

                        if value_str and date_str:
                            recorded_at = datetime.strptime(
                                date_str, "%Y-%m-%d %H:%M:%S %z"
                            ).replace(tzinfo=None)
                            vo2_max_records.append(
                                {
                                    "vo2_max": Decimal(value_str),
                                    "recorded_at": recorded_at,
                                    "source": source or "apple_health",
                                }
                            )

                    elif handler == "sleep":
                        value_str = elem.get("value")
                        start_str = elem.get("startDate")
                        end_str = elem.get("endDate")

                        if value_str and start_str and end_str:
                            stage = SLEEP_VALUE_MAPPING.get(value_str)
                            if stage:
                                start_time = datetime.strptime(
                                    start_str, "%Y-%m-%d %H:%M:%S %z"
                                ).replace(tzinfo=None)
                                end_time = datetime.strptime(
                                    end_str, "%Y-%m-%d %H:%M:%S %z"
                                ).replace(tzinfo=None)
                                duration_minutes = int(
                                    (end_time - start_time).total_seconds() / 60
                                )
                                sleep_raw_records.append(
                                    {
                                        "start": start_time,
                                        "end": end_time,
                                        "value": stage,
                                        "duration_minutes": duration_minutes,
                                    }
                                )

                # Handle Workout elements
                elif elem.tag == "Workout":
                    workout_type_raw = elem.get("workoutActivityType")
                    start_str = elem.get("startDate")
                    end_str = elem.get("endDate")
                    duration_str = elem.get("duration")
                    source = elem.get("sourceName")

                    if workout_type_raw and start_str and end_str and duration_str:
                        workout_type = workout_type_raw.replace(
                            "HKWorkoutActivityType", ""
                        )
                        start_time = datetime.strptime(
                            start_str, "%Y-%m-%d %H:%M:%S %z"
                        ).replace(tzinfo=None)
                        end_time = datetime.strptime(
                            end_str, "%Y-%m-%d %H:%M:%S %z"
                        ).replace(tzinfo=None)

                        workout: WorkoutRecord = {
                            "workout_type": workout_type,
                            "start_time": start_time,
                            "end_time": end_time,
                            "duration_minutes": Decimal(duration_str),
                            "source": source or "apple_health",
                            "indoor_workout": False,
                        }

                        # Parse WorkoutStatistics
                        active_energy = None
                        basal_energy = None
                        distance = None
                        avg_hr = None
                        min_hr = None
                        max_hr = None

                        for stat in elem.findall("WorkoutStatistics"):
                            stat_type = stat.get("type", "")
                            if (
                                stat_type
                                == "HKQuantityTypeIdentifierActiveEnergyBurned"
                            ):
                                active_energy = Decimal(stat.get("sum", "0"))
                            elif (
                                stat_type == "HKQuantityTypeIdentifierBasalEnergyBurned"
                            ):
                                basal_energy = Decimal(stat.get("sum", "0"))
                            elif stat_type in [
                                "HKQuantityTypeIdentifierDistanceWalkingRunning",
                                "HKQuantityTypeIdentifierDistanceCycling",
                                "HKQuantityTypeIdentifierDistanceSwimming",
                            ]:
                                distance = Decimal(stat.get("sum", "0"))
                            elif stat_type == "HKQuantityTypeIdentifierHeartRate":
                                avg_val = stat.get("average")
                                min_val = stat.get("minimum")
                                max_val = stat.get("maximum")
                                if avg_val:
                                    avg_hr = int(float(avg_val))
                                if min_val:
                                    min_hr = int(float(min_val))
                                if max_val:
                                    max_hr = int(float(max_val))

                        # Check metadata for indoor workout
                        for meta in elem.findall("MetadataEntry"):
                            if meta.get("key") == "HKIndoorWorkout":
                                workout["indoor_workout"] = meta.get("value") == "1"

                        # Add optional fields
                        if active_energy is not None:
                            workout["active_energy_kcal"] = active_energy
                        if basal_energy is not None:
                            workout["basal_energy_kcal"] = basal_energy
                        if active_energy is not None and basal_energy is not None:
                            workout["total_energy_kcal"] = active_energy + basal_energy
                        if distance is not None:
                            workout["distance_km"] = distance
                        if avg_hr is not None:
                            workout["avg_heart_rate_bpm"] = avg_hr
                        if min_hr is not None:
                            workout["min_heart_rate_bpm"] = min_hr
                        if max_hr is not None:
                            workout["max_heart_rate_bpm"] = max_hr

                        workout_records.append(workout)

            except (ValueError, TypeError):
                continue
            finally:
                elem.clear()

        print("  ✅ XML parsing complete, aggregating data...")

        # Post-processing: aggregate daily metrics
        # Aggregate steps by date
        steps_by_date: dict = defaultdict(
            lambda: {"value": 0, "source": "apple_health"}
        )
        for record in step_records:
            steps_by_date[record["date"]]["value"] += record["value"]
            steps_by_date[record["date"]]["source"] = record.get(
                "source", "apple_health"
            )

        steps_aggregated = [
            {
                "metric_type": "steps",
                "value": Decimal(str(data["value"])),
                "unit": "count",
                "date": d,
                "recorded_at": datetime.combine(d, datetime.min.time()),
                "source": data["source"],
            }
            for d, data in sorted(steps_by_date.items())
        ]

        # Aggregate active energy by date
        active_energy_by_date: dict = defaultdict(
            lambda: {"value": Decimal("0"), "source": "apple_health"}
        )
        for record in active_energy_records:
            active_energy_by_date[record["date"]]["value"] += record["value"]
            active_energy_by_date[record["date"]]["source"] = record.get(
                "source", "apple_health"
            )

        active_energy_aggregated = [
            {
                "metric_type": "active_energy",
                "value": data["value"],
                "unit": "kcal",
                "date": d,
                "recorded_at": datetime.combine(d, datetime.min.time()),
                "source": data["source"],
            }
            for d, data in sorted(active_energy_by_date.items())
        ]

        # Aggregate exercise minutes by date
        exercise_by_date: dict = defaultdict(
            lambda: {"value": Decimal("0"), "source": "apple_health"}
        )
        for record in exercise_minutes_records:
            exercise_by_date[record["date"]]["value"] += record["value"]
            exercise_by_date[record["date"]]["source"] = record.get(
                "source", "apple_health"
            )

        exercise_aggregated = [
            {
                "metric_type": "exercise_minutes",
                "value": data["value"],
                "unit": "min",
                "date": d,
                "recorded_at": datetime.combine(d, datetime.min.time()),
                "source": data["source"],
            }
            for d, data in sorted(exercise_by_date.items())
        ]

        # Aggregate resting energy by date
        resting_energy_by_date: dict = defaultdict(
            lambda: {"value": Decimal("0"), "source": "apple_health"}
        )
        for record in resting_energy_records:
            resting_energy_by_date[record["date"]]["value"] += record["value"]
            resting_energy_by_date[record["date"]]["source"] = record.get(
                "source", "apple_health"
            )

        resting_energy_aggregated = [
            {
                "metric_type": "resting_energy",
                "value": data["value"],
                "unit": "kcal",
                "date": d,
                "recorded_at": datetime.combine(d, datetime.min.time()),
                "source": data["source"],
            }
            for d, data in sorted(resting_energy_by_date.items())
        ]

        # Aggregate heart rate metrics by date (average multiple readings per day)
        # Resting HR
        resting_hr_by_date: dict[date, list[Decimal]] = defaultdict(list)
        for hr_record in resting_hr_records:
            resting_hr_by_date[hr_record["date"]].append(hr_record["value"])

        resting_hr_aggregated = [
            {
                "metric_type": "resting_heart_rate",
                "value": Decimal(str(sum(values) / len(values))),
                "unit": "bpm",
                "date": d,
                "recorded_at": datetime.combine(d, datetime.min.time()),
                "source": "apple_health",
            }
            for d, values in sorted(resting_hr_by_date.items())
        ]

        # Walking HR
        walking_hr_by_date: dict[date, list[Decimal]] = defaultdict(list)
        for hr_record in walking_hr_records:
            walking_hr_by_date[hr_record["date"]].append(hr_record["value"])

        walking_hr_aggregated = [
            {
                "metric_type": "walking_heart_rate",
                "value": Decimal(str(sum(values) / len(values))),
                "unit": "bpm",
                "date": d,
                "recorded_at": datetime.combine(d, datetime.min.time()),
                "source": "apple_health",
            }
            for d, values in sorted(walking_hr_by_date.items())
        ]

        # HRV (Heart Rate Variability)
        hrv_by_date: dict[date, list[Decimal]] = defaultdict(list)
        for hr_record in hrv_records:
            hrv_by_date[hr_record["date"]].append(hr_record["value"])

        hrv_aggregated = [
            {
                "metric_type": "hrv",
                "value": Decimal(str(sum(values) / len(values))),
                "unit": "ms",
                "date": d,
                "recorded_at": datetime.combine(d, datetime.min.time()),
                "source": "apple_health",
            }
            for d, values in sorted(hrv_by_date.items())
        ]

        # Aggregate sleep into sessions (using 2-hour gap detection)
        sleep_sessions: list[SleepSessionRecord] = []
        if sleep_raw_records:
            sleep_raw_records.sort(key=lambda x: x["start"])
            current_session: list[dict] = []
            GAP_THRESHOLD = timedelta(hours=2)

            for record in sleep_raw_records:
                if not current_session:
                    current_session.append(record)
                else:
                    gap = record["start"] - current_session[-1]["end"]
                    if gap > GAP_THRESHOLD:
                        sleep_sessions.append(
                            self._aggregate_sleep_session(current_session)
                        )
                        current_session = [record]
                    else:
                        current_session.append(record)

            if current_session:
                sleep_sessions.append(self._aggregate_sleep_session(current_session))

        # Sort all results
        weight_records.sort(key=lambda x: x["recorded_at"])
        vo2_max_records.sort(key=lambda x: x["recorded_at"])
        workout_records.sort(key=lambda x: x["start_time"])

        print(f"     Weight: {len(weight_records)} records")
        print(f"     Steps: {len(steps_aggregated)} daily totals")
        print(f"     Active energy: {len(active_energy_aggregated)} daily totals")
        print(f"     Exercise: {len(exercise_aggregated)} daily totals")
        print(f"     Resting energy: {len(resting_energy_aggregated)} daily totals")
        print(f"     Resting HR: {len(resting_hr_aggregated)} daily averages")
        print(f"     Walking HR: {len(walking_hr_aggregated)} daily averages")
        print(f"     HRV: {len(hrv_aggregated)} daily averages")
        print(f"     VO2 max: {len(vo2_max_records)} records")
        print(f"     Sleep: {len(sleep_sessions)} sessions")
        print(f"     Workouts: {len(workout_records)} sessions")

        return {
            "weight": weight_records,
            "steps": steps_aggregated,
            "active_energy": active_energy_aggregated,
            "exercise_minutes": exercise_aggregated,
            "resting_energy": resting_energy_aggregated,
            "resting_hr": resting_hr_aggregated,
            "walking_hr": walking_hr_aggregated,
            "hrv": hrv_aggregated,
            "vo2_max": vo2_max_records,
            "sleep": sleep_sessions,
            "workouts": workout_records,
        }
