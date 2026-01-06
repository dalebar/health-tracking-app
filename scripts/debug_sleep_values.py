#!/usr/bin/env python3
"""
Debug script to see what sleep values actually look like in the export.
Look at RECENT records (2026) to see staged sleep.
"""

from pathlib import Path
from defusedxml import ElementTree as ET

export_path = Path(
    "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
)

print("Looking for RECENT sleep records (2026) in export...")
print()

context = ET.iterparse(export_path, events=("end",))
recent_records = []

for event, elem in context:
    if (
        elem.tag == "Record"
        and elem.get("type") == "HKCategoryTypeIdentifierSleepAnalysis"
    ):
        start_str = elem.get("startDate")
        if start_str and "2026-01" in start_str:  # January 2026 only
            value = elem.get("value")
            start = elem.get("startDate")
            end = elem.get("endDate")

            recent_records.append(f"Value: '{value}' | Start: {start} | End: {end}")

        elem.clear()

# Show first 30 records from 2026
for i, record in enumerate(recent_records[:30]):
    print(record)

print()
print(f"Shown {min(len(recent_records), 30)} records from January 2026")
print(f"Total January 2026 records: {len(recent_records)}")
