"""
Integration tests for Apple Health parser with real XML data.

These tests verify the parser handles realistic scenarios including:
- Multiple records from the same day (aggregation)
- Records spanning multiple days
- Malformed/incomplete XML data
- Edge cases in date handling
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from src.parsers.apple_health_parser import AppleHealthParser


class TestAppleHealthParserIntegration:
    """Test parser with realistic XML data scenarios."""

    def test_parse_multiple_metrics_from_same_day(self):
        """Test handling multiple step records from same day aggregates correctly."""
        xml = """
        <root>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone" unit="count"
                    startDate="2025-12-30 09:00:00 +0000" value="5000"/>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone" unit="count"
                    startDate="2025-12-30 14:30:00 +0000" value="10000"/>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="Apple Watch" unit="count"
                    startDate="2025-12-30 18:00:00 +0000" value="3000"/>
        </root>
        """

        parser = AppleHealthParser()
        results = parser.parse_step_records(xml)

        # Should aggregate all to single day total
        assert len(results) == 1
        assert results[0]["value"] == Decimal("18000")
        assert results[0]["date"] == date(2025, 12, 30)
        assert results[0]["unit"] == "count"
        assert results[0]["metric_type"] == "steps"

    def test_parse_metrics_across_multiple_days(self):
        """Test aggregation correctly separates different days."""
        xml = """
        <root>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone" unit="count"
                    startDate="2025-12-29 23:00:00 +0000" value="1000"/>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone" unit="count"
                    startDate="2025-12-30 01:00:00 +0000" value="2000"/>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone" unit="count"
                    startDate="2025-12-30 12:00:00 +0000" value="3000"/>
        </root>
        """

        parser = AppleHealthParser()
        results = parser.parse_step_records(xml)

        # Should create separate entries for each day
        assert len(results) == 2

        day1 = next(r for r in results if r["date"] == date(2025, 12, 29))
        day2 = next(r for r in results if r["date"] == date(2025, 12, 30))

        assert day1["value"] == Decimal("1000")
        assert day2["value"] == Decimal("5000")  # 2000 + 3000

    def test_handle_malformed_xml_gracefully(self):
        """Test parser skips records with missing required fields."""
        xml = """
        <root>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone" unit="count"
                    startDate="2025-12-30 09:00:00 +0000" value="5000"/>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone" unit="count"
                    startDate="2025-12-30 10:00:00 +0000"/>
            <Record type="HKQuantityTypeIdentifierStepCount"
                    sourceName="iPhone"
                    startDate="2025-12-30 11:00:00 +0000" value="3000"/>
        </root>
        """

        parser = AppleHealthParser()
        results = parser.parse_step_records(xml)

        # Should skip malformed records but process valid ones
        assert len(results) == 1
        assert results[0]["value"] == Decimal("5000")

    def test_parse_weight_with_different_sources(self):
        """Test weight records preserve source information."""
        xml1 = """
        <Record type="HKQuantityTypeIdentifierBodyMass"
                sourceName="Health" unit="kg"
                startDate="2025-12-30 08:00:00 +0000" value="100.5"/>
        """

        xml2 = """
        <Record type="HKQuantityTypeIdentifierBodyMass"
                sourceName="Withings" unit="kg"
                startDate="2025-12-30 08:00:00 +0000" value="100.5"/>
        """

        parser = AppleHealthParser()
        result1 = parser.parse_weight_record(xml1)
        result2 = parser.parse_weight_record(xml2)

        assert result1["source"] == "Health"
        assert result2["source"] == "Withings"
        assert result1["value"] == result2["value"]

    def test_parse_weight_missing_required_field(self):
        """Test weight parser raises error for missing required fields."""
        xml_no_value = """
        <Record type="HKQuantityTypeIdentifierBodyMass"
                sourceName="Health" unit="kg"
                startDate="2025-12-30 08:00:00 +0000"/>
        """

        parser = AppleHealthParser()
        with pytest.raises(ValueError, match="Missing required attribute: value"):
            parser.parse_weight_record(xml_no_value)

    def test_parse_weight_missing_date(self):
        """Test weight parser raises error for missing date."""
        xml_no_date = """
        <Record type="HKQuantityTypeIdentifierBodyMass"
                sourceName="Health" unit="kg"
                value="100.5"/>
        """

        parser = AppleHealthParser()
        with pytest.raises(ValueError, match="Missing required attribute: startDate"):
            parser.parse_weight_record(xml_no_date)

    def test_decimal_precision_maintained(self):
        """Test that decimal values maintain precision through parsing."""
        xml = """
        <Record type="HKQuantityTypeIdentifierBodyMass"
                sourceName="Health" unit="kg"
                startDate="2025-12-30 08:00:00 +0000" value="114.567"/>
        """

        parser = AppleHealthParser()
        result = parser.parse_weight_record(xml)

        # Should maintain 3 decimal places
        assert result["value"] == Decimal("114.567")
        assert str(result["value"]) == "114.567"

    def test_timezone_handling(self):
        """Test that timezone information is correctly stripped."""
        xml = """
        <Record type="HKQuantityTypeIdentifierBodyMass"
                sourceName="Health" unit="kg"
                startDate="2025-12-30 14:30:00 +0100" value="100.0"/>
        """

        parser = AppleHealthParser()
        result = parser.parse_weight_record(xml)

        # Should parse time correctly and strip timezone
        assert result["recorded_at"] == datetime(2025, 12, 30, 14, 30, 0)
        assert result["recorded_at"].tzinfo is None

    def test_empty_result_set(self):
        """Test parser handles XML with no matching records."""
        xml = """
        <root>
            <Record type="HKQuantityTypeIdentifierHeartRate"
                    sourceName="Apple Watch" unit="count/min"
                    startDate="2025-12-30 09:00:00 +0000" value="70"/>
        </root>
        """

        parser = AppleHealthParser()
        results = parser.parse_step_records(xml)

        # Should return empty list, not error
        assert results == []
        assert isinstance(results, list)
