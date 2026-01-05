"""
Apple Health XML parser for extracting health metrics.
"""

from collections import defaultdict
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any

from defusedxml import ElementTree as ET


class AppleHealthParser:
    """Parser for Apple Health export XML files."""

    def parse_weight_record(self, xml_string: str) -> Dict[str, Any]:
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

    def parse_weight_from_file(self, file_path: str | Path) -> list[Dict[str, Any]]:
        """
        Parse all weight records from Apple Health export XML file.

        Args:
            file_path: Path to export.xml file

        Returns:
            List of weight records sorted by date (oldest first)
        """
        # Parse XML file in chunks to handle large files efficiently
        results = []

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

    def parse_step_records(self, xml_string: str) -> list[Dict[str, Any]]:
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
            value_str = record.get("value")
            date_str = record.get("startDate")

            if not value_str or not date_str:
                continue

            value = Decimal(value_str)
            recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
            record_date = recorded_at.date()

            daily_steps[record_date] += value

        # Convert to list of results
        results = []
        for record_date, total_steps in daily_steps.items():
            results.append(
                {
                    "metric_type": "steps",
                    "value": total_steps,
                    "unit": "count",
                    "date": datetime.combine(record_date, datetime.min.time()),
                    "source": "apple_health",
                }
            )

        return results
