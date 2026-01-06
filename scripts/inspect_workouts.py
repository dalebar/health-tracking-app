#!/usr/bin/env python3
"""
Inspect workout structure in Apple Health export - DETAILED VERSION.
"""

from pathlib import Path
from defusedxml import ElementTree as ET
from collections import Counter

export_path = Path(
    "/Users/daleb/Documents/health/apple_health_export_2026/apple_health_export/export.xml"
)

print("=" * 70)
print("WORKOUT STRUCTURE INSPECTION")
print("=" * 70)
print()

# Track workout types
workout_types = Counter()
workouts_with_energy = 0
workouts_with_distance = 0
workouts_with_hr = 0

context = ET.iterparse(export_path, events=("end",))
workout_count = 0

for event, elem in context:
    if elem.tag == "Workout":
        workout_count += 1
        workout_type = elem.get("workoutActivityType", "Unknown")
        workout_types[workout_type] += 1

        # Show first Apple Watch workout in detail
        if workout_count <= 2 and elem.get("sourceName") == "dTime":
            print(f"📋 WORKOUT #{workout_count} - DETAILED VIEW")
            print(f"Type: {workout_type}")
            print(f"Start: {elem.get('startDate')}")
            print(f"End: {elem.get('endDate')}")
            print(f"Duration: {elem.get('duration')} minutes")
            print(f"Source: {elem.get('sourceName')}")
            print()

            # Inspect WorkoutStatistics
            print("  📊 WorkoutStatistics:")
            for stat in elem.findall("WorkoutStatistics"):
                stat_type = stat.get("type")
                avg = stat.get("average")
                minimum = stat.get("minimum")
                maximum = stat.get("maximum")
                total = stat.get("sum")
                unit = stat.get("unit")

                print(f"    - {stat_type}:")
                if avg:
                    print(f"      Average: {avg} {unit}")
                if minimum:
                    print(f"      Min: {minimum} {unit}")
                if maximum:
                    print(f"      Max: {maximum} {unit}")
                if total:
                    print(f"      Total: {total} {unit}")

            print()
            print("  🏷️  MetadataEntry (first 5):")
            for i, meta in enumerate(elem.findall("MetadataEntry")[:5]):
                key = meta.get("key")
                value = meta.get("value")
                print(f"    - {key}: {value}")

            print()
            print("  🎯 WorkoutEvent (first 3):")
            for i, event_elem in enumerate(elem.findall("WorkoutEvent")[:3]):
                event_type = event_elem.get("type")
                date = event_elem.get("date")
                print(f"    - {event_type} at {date}")

            print()
            print("-" * 70)
            print()

        # Count workouts with specific metrics
        for stat in elem.findall("WorkoutStatistics"):
            stat_type = stat.get("type", "")
            if "Energy" in stat_type:
                workouts_with_energy += 1
            if "Distance" in stat_type:
                workouts_with_distance += 1
            if "HeartRate" in stat_type:
                workouts_with_hr += 1

        elem.clear()

# Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total workouts: {workout_count}")
print(f"Workouts with energy data: {workouts_with_energy}")
print(f"Workouts with distance data: {workouts_with_distance}")
print(f"Workouts with heart rate data: {workouts_with_hr}")
print()

print("Workout Types:")
for workout_type, count in workout_types.most_common():
    # Clean up the type name
    clean_name = workout_type.replace("HKWorkoutActivityType", "")
    print(f"  {clean_name}: {count}")
