"""
Overview page - Weekly summary and key metrics.
"""

import streamlit as st
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.dashboard.utils.api_client import HealthAPIClient

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")

st.title("📊 Overview")
st.markdown("Quick summary of your health metrics and recent progress.")

# Initialize API client
api = HealthAPIClient()

# Date range for "this week"
today = date.today()
week_start = today - timedelta(days=7)

# Fetch data
try:
    # Weight
    latest_weight = api.get_latest_weight()
    weight_trend = api.get_weight_trend(days=7)

    # Activity
    activity_summary = api.get_activity_summary(week_start, today)

    # Workouts
    workouts = api.list_workouts(start_date=week_start, end_date=today, limit=100)
    workout_stats = api.get_workout_stats_by_type(start_date=week_start, end_date=today)

    # Display metrics
    st.header("This Week's Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Current Weight",
            f"{float(latest_weight['value']):.1f} kg",
            delta=f"{float(weight_trend['change']):.1f} kg (7 days)",
            delta_color="inverse",
        )

    with col2:
        st.metric(
            "Workouts Completed",
            workouts["count"],
            delta=f"{float(workouts['total_duration_minutes']):.0f} min total",
        )

    with col3:
        st.metric(
            "Avg Daily Steps",
            f"{float(activity_summary['avg_steps_per_day']):.0f}",
            delta=f"{float(activity_summary['total_steps']):.0f} total",
        )

    with col4:
        st.metric(
            "Avg Calories Burned",
            f"{float(activity_summary['avg_active_energy_per_day']):.0f} kcal/day",
            delta=f"{float(activity_summary['total_active_energy']):.0f} total",
        )

    st.divider()

    # Workout breakdown
    if workout_stats:
        st.subheader("Workout Breakdown (Last 7 Days)")

        cols = st.columns(len(workout_stats))
        for idx, stat in enumerate(workout_stats):
            with cols[idx]:
                st.metric(
                    stat["workout_type"],
                    f"{stat['count']} sessions",
                    delta=f"{float(stat['avg_calories']):.0f} kcal avg",
                )

    st.divider()

    # Recent workouts
    st.subheader("Recent Workouts")

    if workouts["workouts"]:
        for workout in workouts["workouts"][:5]:  # Show last 5
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

            with col1:
                st.write(f"**{workout['workout_type']}**")
            with col2:
                st.write(workout["start_time"].split("T")[0])
            with col3:
                st.write(f"{float(workout['duration_minutes']):.0f} min")
            with col4:
                if workout.get("total_energy_kcal"):
                    st.write(f"{float(workout['total_energy_kcal']):.0f} kcal")
    else:
        st.info("No workouts recorded this week.")

    st.divider()

    # Progress to goal
    st.subheader("Progress to Goal")

    current = float(latest_weight["value"])
    goal = 100.0
    remaining = current - goal
    progress = ((114.5 - current) / (114.5 - goal)) * 100

    st.progress(progress / 100)
    st.write(f"**{progress:.1f}%** complete | **{remaining:.1f} kg** remaining")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the FastAPI server is running at http://localhost:8000")
