"""Unit tests for workout parser."""

import pytest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from src.parsers.apple_health_parser import AppleHealthParser


@pytest.fixture
def sample_workout_xml():
    """Create sample workout XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <HealthData locale="en_US">
        <Workout workoutActivityType="HKWorkoutActivityTypeBoxing"
                 duration="60"
                 durationUnit="min"
                 totalDistance="0"
                 totalDistanceUnit="km"
                 totalEnergyBurned="450"
                 totalEnergyBurnedUnit="kcal"
                 sourceName="Apple Watch"
                 sourceVersion="10.2"
                 creationDate="2025-01-05 18:30:00 +0000"
                 startDate="2025-01-05 17:30:00 +0000"
                 endDate="2025-01-05 18:30:00 +0000">
            <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate"
                              startDate="2025-01-05 17:30:00 +0000"
                              endDate="2025-01-05 18:30:00 +0000"
                              average="145"
                              minimum="100"
                              maximum="180"
                              unit="count/min"/>
            <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned"
                              startDate="2025-01-05 17:30:00 +0000"
                              endDate="2025-01-05 18:30:00 +0000"
                              sum="450"
                              unit="kcal"/>
            <WorkoutStatistics type="HKQuantityTypeIdentifierBasalEnergyBurned"
                              startDate="2025-01-05 17:30:00 +0000"
                              endDate="2025-01-05 18:30:00 +0000"
                              sum="80"
                              unit="kcal"/>
        </Workout>
        <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
                 duration="30"
                 durationUnit="min"
                 totalDistance="5.2"
                 totalDistanceUnit="km"
                 totalEnergyBurned="350"
                 totalEnergyBurnedUnit="kcal"
                 sourceName="Apple Watch"
                 sourceVersion="10.2"
                 creationDate="2025-01-06 08:00:00 +0000"
                 startDate="2025-01-06 07:00:00 +0000"
                 endDate="2025-01-06 07:30:00 +0000">
            <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning"
                              startDate="2025-01-06 07:00:00 +0000"
                              endDate="2025-01-06 07:30:00 +0000"
                              sum="5.2"
                              unit="km"/>
            <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate"
                              startDate="2025-01-06 07:00:00 +0000"
                              endDate="2025-01-06 07:30:00 +0000"
                              average="155"
                              minimum="120"
                              maximum="175"
                              unit="count/min"/>
            <MetadataEntry key="HKIndoorWorkout" value="0"/>
        </Workout>
    </HealthData>
    """


def test_parse_workouts_from_file(sample_workout_xml):
    """Test parsing workouts from XML file."""
    with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(sample_workout_xml)
        f.flush()
        temp_path = Path(f.name)

    try:
        parser = AppleHealthParser()
        workouts = parser.parse_workouts_from_file(temp_path)

        # Should find 2 workouts
        assert len(workouts) == 2

        # Test Boxing workout
        boxing = workouts[0]
        assert boxing["workout_type"] == "Boxing"
        assert boxing["start_time"] == datetime(2025, 1, 5, 17, 30, 0)
        assert boxing["end_time"] == datetime(2025, 1, 5, 18, 30, 0)
        assert boxing["duration_minutes"] == 60
        assert boxing["active_energy_kcal"] == Decimal("450")
        assert boxing["basal_energy_kcal"] == Decimal("80")
        assert boxing["total_energy_kcal"] == Decimal("530")
        assert "distance_km" not in boxing  # No distance for boxing
        assert boxing["avg_heart_rate_bpm"] == 145
        assert boxing["min_heart_rate_bpm"] == 100
        assert boxing["max_heart_rate_bpm"] == 180
        assert boxing["indoor_workout"] is False  # Default value
        assert boxing["source"] == "Apple Watch"

        # Test Running workout
        running = workouts[1]
        assert running["workout_type"] == "Running"
        assert running["start_time"] == datetime(2025, 1, 6, 7, 0, 0)
        assert running["end_time"] == datetime(2025, 1, 6, 7, 30, 0)
        assert running["duration_minutes"] == 30
        assert running["distance_km"] == Decimal("5.2")
        assert running["avg_heart_rate_bpm"] == 155
        assert running["indoor_workout"] is False
        assert running["source"] == "Apple Watch"
    finally:
        temp_path.unlink()


def test_parse_workouts_empty_file():
    """Test parsing workouts from empty XML file."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <HealthData locale="en_US">
    </HealthData>
    """

    with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(xml_content)
        f.flush()
        temp_path = Path(f.name)

    try:
        parser = AppleHealthParser()
        workouts = parser.parse_workouts_from_file(temp_path)

        # Should return empty list
        assert workouts == []
    finally:
        temp_path.unlink()
