#!/usr/bin/env python3
"""
Search for sleep score data in Apple Health export.
"""

from pathlib import Path
from defusedxml import ElementTree as ET

export_path = Path(
    "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
)

print("Searching for sleep score records...")
print()

# Search for any records containing "sleep" and "score" in type name
sleep_score_records = []
context = ET.iterparse(export_path, events=("end",))

for event, elem in context:
    if elem.tag == "Record":
        record_type = elem.get("type", "")

        # Look for anything with "Sleep" and "Score" in the name
        if "sleep" in record_type.lower() and "score" in record_type.lower():
            start = elem.get("startDate")
            value = elem.get("value")

            # Only show 2026 records
            if start and "2026-01" in start:
                sleep_score_records.append(
                    {"type": record_type, "value": value, "start": start}
                )

        # Also check for Duration, Bedtime, Interruption components
        if any(word in record_type for word in ["Duration", "Bedtime", "Interruption"]):
            if "sleep" in record_type.lower():
                start = elem.get("startDate")
                value = elem.get("value")

                if start and "2026-01" in start:
                    sleep_score_records.append(
                        {"type": record_type, "value": value, "start": start}
                    )

    elem.clear()

# Show results
if sleep_score_records:
    print(f"Found {len(sleep_score_records)} sleep score-related records:")
    print()

    for i, record in enumerate(sleep_score_records[:30]):
        print(f"Type: {record['type']}")
        print(f"Value: {record['value']}")
        print(f"Date: {record['start']}")
        print()
else:
    print("❌ No sleep score records found")
    print()
    print("Possible reasons:")
    print("1. Sleep Score is iOS 17+ feature (requires newer iOS)")
    print("2. Might be stored in a different format")
    print("3. May not be included in XML export")

print(f"Total records found: {len(sleep_score_records)}")
