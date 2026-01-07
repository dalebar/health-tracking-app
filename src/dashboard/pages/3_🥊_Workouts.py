"""
Workouts page - Training history and performance analysis.
"""

import streamlit as st
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.dashboard.utils.api_client import HealthAPIClient
from src.dashboard.utils.charts import (
    create_workout_pie_chart,
    create_boxing_performance_chart,
)

st.set_page_config(page_title="Workouts", page_icon="🥊", layout="wide")

st.title("🥊 Workout Analysis")
st.markdown("Track your training sessions and performance metrics.")

# Initialize API client
api = HealthAPIClient()

# Sidebar filters
st.sidebar.header("Filters")

# Date range
days_options = {
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Last 6 months": 180,
    "Last year": 365,
    "All time": None,
}
selected_range = st.sidebar.selectbox("Date Range", list(days_options.keys()), index=1)
days = days_options[selected_range]

today = date.today()
start_date = today - timedelta(days=days) if days else None

# Workout type filter
workout_type_filter = st.sidebar.selectbox(
    "Workout Type",
    [
        "All",
        "Boxing",
        "Functional Strength Training",
        "Traditional Strength Training",
        "Other",
    ],
)
workout_type = None if workout_type_filter == "All" else workout_type_filter

# Fetch data
try:
    # Workout stats
    workout_stats = api.get_workout_stats_by_type(start_date=start_date, end_date=today)

    # Workouts list
    workouts = api.list_workouts(
        workout_type=workout_type, start_date=start_date, end_date=today, limit=200
    )

    # Display summary metrics
    st.header("Summary Statistics")

    if workout_stats:
        # Overall totals
        total_workouts = sum(s["count"] for s in workout_stats)
        total_duration = sum(float(s["total_duration_minutes"]) for s in workout_stats)
        total_calories = sum(float(s["total_calories"]) for s in workout_stats)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Workouts", total_workouts)

        with col2:
            st.metric("Total Duration", f"{total_duration:.0f} min")

        with col3:
            st.metric("Total Calories", f"{total_calories:.0f} kcal")

        with col4:
            avg_duration = total_duration / total_workouts if total_workouts > 0 else 0
            st.metric("Avg Duration", f"{avg_duration:.0f} min")

        st.divider()

        # Workout type distribution
        st.header("Workout Type Distribution")

        col1, col2 = st.columns([1, 1])

        with col1:
            fig = create_workout_pie_chart(workout_stats)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Breakdown by Type")
            for stat in workout_stats:
                st.write(f"**{stat['workout_type']}**")
                st.write(f"- Sessions: {stat['count']}")
                st.write(
                    f"- Total Duration: {float(stat['total_duration_minutes']):.0f} min"
                )
                st.write(
                    f"- Avg Duration: {float(stat['avg_duration_minutes']):.0f} min"
                )
                st.write(f"- Total Calories: {float(stat['total_calories']):.0f} kcal")
                if stat.get("avg_heart_rate"):
                    st.write(
                        f"- Avg Heart Rate: {float(stat['avg_heart_rate']):.0f} bpm"
                    )
                st.write("")

        st.divider()

        # Boxing performance over time (if boxing data exists)
        boxing_stats = [s for s in workout_stats if "Boxing" in s["workout_type"]]
        if boxing_stats:
            st.header("Boxing Performance Trends")

            # Get boxing workouts for chart
            boxing_workouts = api.list_workouts(
                workout_type="Boxing", start_date=start_date, end_date=today, limit=200
            )

            if boxing_workouts["workouts"]:
                # Reverse to show oldest first
                boxing_data = list(reversed(boxing_workouts["workouts"]))
                fig = create_boxing_performance_chart(boxing_data)
                st.plotly_chart(fig, use_container_width=True)

            st.divider()

    else:
        st.info("No workout data available for the selected period.")

    # Recent workouts table
    st.header("Recent Workouts")

    if workouts["workouts"]:
        workout_data = []
        for w in workouts["workouts"][:20]:  # Show last 20
            workout_data.append(
                {
                    "Date": w["start_time"].split("T")[0],
                    "Type": w["workout_type"],
                    "Duration (min)": f"{float(w['duration_minutes']):.0f}",
                    "Calories (kcal)": (
                        f"{float(w.get('total_energy_kcal', 0)):.0f}"
                        if w.get("total_energy_kcal")
                        else "N/A"
                    ),
                    "Avg HR (bpm)": str(w.get("avg_heart_rate_bpm", "N/A")),
                    "Distance (km)": (
                        f"{float(w.get('distance_km', 0)):.2f}"
                        if w.get("distance_km")
                        else "N/A"
                    ),
                }
            )

        st.dataframe(workout_data, use_container_width=True)
    else:
        st.info("No workouts found for the selected filters.")

    # Training consistency
    st.divider()
    st.header("Training Consistency")

    if workouts["count"] > 0 and days:
        workouts_per_week = (workouts["count"] / days) * 7
        st.metric(
            "Average Workouts per Week",
            f"{workouts_per_week:.1f}",
            delta=f"{workouts['count']} in {days} days",
        )

        # Calculate streak (would need more API support for this)
        st.info("💡 Workout streaks and detailed consistency metrics coming soon!")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the FastAPI server is running at http://localhost:8000")
