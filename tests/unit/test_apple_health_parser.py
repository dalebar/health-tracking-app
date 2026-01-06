"""
Unit tests for Apple Health XML parser.

Tests follow TDD methodology: write test first, then implementation.
"""

from datetime import datetime
from decimal import Decimal
from src.parsers.apple_health_parser import AppleHealthParser


class TestAppleHealthParser:
    """Test suite for Apple Health XML parser."""

    def test_parse_single_weight_record(self):
        """Test parsing a single weight measurement from XML."""
        xml_string = """
        <Record type="HKQuantityTypeIdentifierBodyMass"
                sourceName="Health"
                unit="kg"
                startDate="2025-06-26 06:53:00 +0000"
                value="112.5"/>
        """

        parser = AppleHealthParser()
        result = parser.parse_weight_record(xml_string)

        # Assertions
        assert result["metric_type"] == "weight"
        assert result["value"] == Decimal("112.5")
        assert result["unit"] == "kg"
        assert result["recorded_at"] == datetime(2025, 6, 26, 6, 53, 0)
        assert result["source"] == "Health"

    def test_parse_step_records_aggregation(self):
        """Test aggregating multiple step records for a single day."""
        xml_string = """
        <root>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone"
                    unit="count"
                    startDate="2025-06-26 10:00:00 +0000"
                    value="648"/>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone"
                    unit="count"
                    startDate="2025-06-26 14:30:00 +0000"
                    value="752"/>
        </root>
        """

        parser = AppleHealthParser()
        results = parser.parse_step_records(xml_string)

        # Should aggregate to single daily total
        assert len(results) == 1
        assert results[0]["metric_type"] == "steps"
        assert results[0]["value"] == Decimal("1400")  # 648 + 752
        assert results[0]["unit"] == "count"
        assert results[0]["date"] == datetime(2025, 6, 26).date()

    def test_sleep_session_grouping(self):
        """Test that 2-hour gap detection groups sessions correctly."""
        from pathlib import Path
        from tempfile import NamedTemporaryFile

        # Create XML with two separate sleep sessions (>2 hours apart)
        xml_content = """<?xml version="1.0"?>
        <HealthData>
            <Record type="HKCategoryTypeIdentifierSleepAnalysis"
                    value="HKCategoryValueSleepAnalysisAsleepCore"
                    startDate="2025-06-26 22:00:00 +0000"
                    endDate="2025-06-27 06:00:00 +0000"/>
            <Record type="HKCategoryTypeIdentifierSleepAnalysis"
                    value="HKCategoryValueSleepAnalysisAsleepCore"
                    startDate="2025-06-27 14:00:00 +0000"
                    endDate="2025-06-27 15:00:00 +0000"/>
        </HealthData>
        """

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            parser = AppleHealthParser()
            results = parser.parse_sleep_from_file(temp_path)

            # Should create 2 separate sessions due to >2 hour gap
            assert len(results) == 2

            # First session: 8 hours (night sleep)
            assert results[0]["start_time"] == datetime(2025, 6, 26, 22, 0, 0)
            assert results[0]["end_time"] == datetime(2025, 6, 27, 6, 0, 0)
            assert results[0]["total_duration_minutes"] == 480

            # Second session: 1 hour (nap)
            assert results[1]["start_time"] == datetime(2025, 6, 27, 14, 0, 0)
            assert results[1]["end_time"] == datetime(2025, 6, 27, 15, 0, 0)
            assert results[1]["total_duration_minutes"] == 60
        finally:
            temp_path.unlink()

    def test_sleep_stage_aggregation(self):
        """Test that sleep stages sum correctly within session."""
        from pathlib import Path
        from tempfile import NamedTemporaryFile

        # Create XML with multiple sleep stages in one session
        xml_content = """<?xml version="1.0"?>
        <HealthData>
            <Record type="HKCategoryTypeIdentifierSleepAnalysis"
                    value="HKCategoryValueSleepAnalysisAsleepDeep"
                    startDate="2025-06-26 22:00:00 +0000"
                    endDate="2025-06-26 23:30:00 +0000"/>
            <Record type="HKCategoryTypeIdentifierSleepAnalysis"
                    value="HKCategoryValueSleepAnalysisAsleepCore"
                    startDate="2025-06-26 23:30:00 +0000"
                    endDate="2025-06-27 04:00:00 +0000"/>
            <Record type="HKCategoryTypeIdentifierSleepAnalysis"
                    value="HKCategoryValueSleepAnalysisAsleepREM"
                    startDate="2025-06-27 04:00:00 +0000"
                    endDate="2025-06-27 05:30:00 +0000"/>
            <Record type="HKCategoryTypeIdentifierSleepAnalysis"
                    value="HKCategoryValueSleepAnalysisAwake"
                    startDate="2025-06-27 05:30:00 +0000"
                    endDate="2025-06-27 06:00:00 +0000"/>
        </HealthData>
        """

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            parser = AppleHealthParser()
            results = parser.parse_sleep_from_file(temp_path)

            # Should create single session with all stages
            assert len(results) == 1

            session = results[0]
            # Deep: 90 min, Core: 270 min, REM: 90 min, Awake: 30 min
            # Total: 480 minutes (8 hours)
            assert session["total_duration_minutes"] == 480
            assert session["deep_minutes"] == 90
            assert session["core_minutes"] == 270
            assert session["rem_minutes"] == 90
            assert session["awake_minutes"] == 30
        finally:
            temp_path.unlink()
