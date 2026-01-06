#!/usr/bin/env python3
"""
Inspect heart rate data in workouts.
"""

from pathlib import Path
from defusedxml import ElementTree as ET

export_path = Path(
    "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
)

print("=" * 70)
print("HEART RATE DATA INSPECTION")
print("=" * 70)
print()

context = ET.iterparse(export_path, events=("end",))
workout_count = 0
boxing_count = 0

for event, elem in context:
    if elem.tag == "Workout":
        workout_count += 1
        workout_type = elem.get("workoutActivityType", "")

        # Find a boxing workout with heart rate data
        if "Boxing" in workout_type and boxing_count < 2:
            has_hr = False
            for stat in elem.findall("WorkoutStatistics"):
                if "HeartRate" in stat.get("type", ""):
                    has_hr = True
                    break

            if has_hr:
                boxing_count += 1
                print(f"🥊 BOXING WORKOUT #{boxing_count}")
                print(f"Start: {elem.get('startDate')}")
                print(f"End: {elem.get('endDate')}")
                print(f"Duration: {elem.get('duration')} minutes")
                print()

                # Show all WorkoutStatistics
                print("  📊 ALL WorkoutStatistics:")
                for stat in elem.findall("WorkoutStatistics"):
                    stat_type = stat.get("type", "")
                    print(f"    Type: {stat_type}")

                    # Show all attributes
                    for attr_name in ["average", "minimum", "maximum", "sum", "unit"]:
                        attr_value = stat.get(attr_name)
                        if attr_value:
                            print(f"      {attr_name}: {attr_value}")
                    print()

                # Check metadata for HR zones
                print("  🏷️  Metadata (looking for HR zones):")
                for meta in elem.findall("MetadataEntry"):
                    key = meta.get("key", "")
                    value = meta.get("value", "")
                    # Show anything with "Zone", "Heart", or "HR"
                    if any(
                        word in key for word in ["Zone", "Heart", "HR", "Elevation"]
                    ):
                        print(f"    {key}: {value}")

                print()
                print("-" * 70)
                print()

        elem.clear()

print(f"Total workouts scanned: {workout_count}")
print(f"Boxing workouts with HR shown: {boxing_count}")
