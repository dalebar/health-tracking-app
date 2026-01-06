"""Unit tests for VO2 max parser."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from src.parsers.apple_health_parser import AppleHealthParser


class TestVO2MaxParser:
    """Test suite for VO2 max parsing."""

    def test_parse_single_vo2_max_record(self):
        """Test parsing a single VO2 max measurement."""
        xml_content = """<?xml version="1.0"?>
        <HealthData>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    startDate="2025-06-15 08:30:00 +0000"
                    value="42.5"/>
        </HealthData>
        """

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            parser = AppleHealthParser()
            results = parser.parse_vo2_max_from_file(temp_path)

            assert len(results) == 1
            assert results[0]["vo2_max"] == Decimal("42.5")
            assert results[0]["recorded_at"] == datetime(2025, 6, 15, 8, 30, 0)
            assert results[0]["source"] == "Apple Watch"
        finally:
            temp_path.unlink()

    def test_parse_multiple_vo2_max_records(self):
        """Test parsing and sorting multiple VO2 max measurements."""
        xml_content = """<?xml version="1.0"?>
        <HealthData>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    startDate="2025-06-20 10:00:00 +0000"
                    value="44.2"/>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    startDate="2025-06-15 08:30:00 +0000"
                    value="42.5"/>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    startDate="2025-06-25 09:15:00 +0000"
                    value="45.1"/>
        </HealthData>
        """

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            parser = AppleHealthParser()
            results = parser.parse_vo2_max_from_file(temp_path)

            # Should return 3 records
            assert len(results) == 3

            # Should be sorted by date (earliest first)
            assert results[0]["recorded_at"] == datetime(2025, 6, 15, 8, 30, 0)
            assert results[0]["vo2_max"] == Decimal("42.5")

            assert results[1]["recorded_at"] == datetime(2025, 6, 20, 10, 0, 0)
            assert results[1]["vo2_max"] == Decimal("44.2")

            assert results[2]["recorded_at"] == datetime(2025, 6, 25, 9, 15, 0)
            assert results[2]["vo2_max"] == Decimal("45.1")
        finally:
            temp_path.unlink()

    def test_handle_missing_fields(self):
        """Test skipping records with missing required fields."""
        xml_content = """<?xml version="1.0"?>
        <HealthData>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    startDate="2025-06-15 08:30:00 +0000"
                    value="42.5"/>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    startDate="2025-06-16 09:00:00 +0000"/>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    value="43.0"/>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    sourceName="Apple Watch"
                    unit="mL/min·kg"
                    startDate="2025-06-17 10:00:00 +0000"
                    value="43.5"/>
        </HealthData>
        """

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            parser = AppleHealthParser()
            results = parser.parse_vo2_max_from_file(temp_path)

            # Should only return 2 valid records (skipping those with missing fields)
            assert len(results) == 2
            assert results[0]["vo2_max"] == Decimal("42.5")
            assert results[1]["vo2_max"] == Decimal("43.5")
        finally:
            temp_path.unlink()

    def test_default_source_when_missing(self):
        """Test that default source is used when sourceName is missing."""
        xml_content = """<?xml version="1.0"?>
        <HealthData>
            <Record type="HKQuantityTypeIdentifierVO2Max"
                    unit="mL/min·kg"
                    startDate="2025-06-15 08:30:00 +0000"
                    value="42.5"/>
        </HealthData>
        """

        with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            parser = AppleHealthParser()
            results = parser.parse_vo2_max_from_file(temp_path)

            assert len(results) == 1
            assert results[0]["source"] == "apple_health"  # Default source
        finally:
            temp_path.unlink()
