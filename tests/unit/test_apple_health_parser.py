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
