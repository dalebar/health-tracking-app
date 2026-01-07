"""
Weight page - Weight loss progress and trends.
"""

import streamlit as st
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.dashboard.utils.api_client import HealthAPIClient
from src.dashboard.utils.charts import create_weight_trend_chart

st.set_page_config(page_title="Weight", page_icon="⚖️", layout="wide")

st.title("⚖️ Weight Tracking")
st.markdown("Monitor your weight loss progress and trends over time.")

# Initialize API client
api = HealthAPIClient()

# Date range selector
st.sidebar.header("Date Range")
default_days = 90
days_options = {
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Last 6 months": 180,
    "Last year": 365,
}
selected_range = st.sidebar.selectbox(
    "Select range", list(days_options.keys()), index=1
)
days = days_options[selected_range]

today = date.today()
start_date = today - timedelta(days=days)

# Fetch data
try:
    # Latest weight
    latest_weight = api.get_latest_weight()

    # Weight trend
    weight_trend = api.get_weight_trend(days=days)

    # Weight history
    weight_history = api.get_weight_history(
        start_date=start_date, end_date=today, limit=500
    )

    # Display current stats
    st.header("Current Status")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Current Weight",
            f"{float(latest_weight['value']):.1f} kg",
        )

    with col2:
        st.metric(
            "Goal Weight",
            "100.0 kg",
            delta=f"{float(latest_weight['value']) - 100.0:.1f} kg to go",
        )

    with col3:
        st.metric(
            f"Change ({days} days)",
            f"{float(weight_trend['change']):.1f} kg",
            delta=f"{float(weight_trend['change_percentage']):.1f}%",
            delta_color="inverse",
        )

    with col4:
        avg_7_day = weight_trend.get("average_7_day")
        if avg_7_day:
            st.metric(
                "7-Day Average",
                f"{float(avg_7_day):.1f} kg",
            )
        else:
            st.metric("7-Day Average", "N/A")

    st.divider()

    # Weight trend chart
    st.header("Weight Progress")

    if weight_history["measurements"]:
        # Reverse to show oldest first
        measurements = list(reversed(weight_history["measurements"]))
        fig = create_weight_trend_chart(measurements, goal_weight=100.0)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No weight data available for the selected period.")

    st.divider()

    # Trend analysis
    st.header("Trend Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Summary")
        st.write(f"**Start Weight:** {float(weight_trend['start_weight']):.1f} kg")
        st.write(f"**Current Weight:** {float(weight_trend['current_weight']):.1f} kg")
        st.write(f"**Total Change:** {float(weight_trend['change']):.1f} kg")
        st.write(f"**Change %:** {float(weight_trend['change_percentage']):.1f}%")
        st.write(f"**Days Tracked:** {weight_trend['days_tracked']}")

    with col2:
        st.subheader("Averages")
        avg_7 = weight_trend.get("average_7_day")
        avg_30 = weight_trend.get("average_30_day")

        if avg_7:
            st.write(f"**7-Day Average:** {float(avg_7):.1f} kg")
        else:
            st.write("**7-Day Average:** Not enough data")

        if avg_30:
            st.write(f"**30-Day Average:** {float(avg_30):.1f} kg")
        else:
            st.write("**30-Day Average:** Not enough data")

        # Calculate average weekly loss if we have data
        if weight_trend["days_tracked"] > 0:
            weeks = weight_trend["days_tracked"] / 7
            avg_weekly_loss = float(weight_trend["change"]) / weeks if weeks > 0 else 0
            st.write(f"**Avg Weekly Change:** {avg_weekly_loss:.2f} kg/week")

    st.divider()

    # Recent measurements
    st.header("Recent Measurements")

    if weight_history["measurements"]:
        # Show last 10 measurements
        st.dataframe(
            [
                {
                    "Date": m["recorded_at"].split("T")[0],
                    "Weight (kg)": f"{float(m['value']):.1f}",
                    "Source": m.get("source", "N/A"),
                }
                for m in weight_history["measurements"][:10]
            ],
            use_container_width=True,
        )
    else:
        st.info("No recent measurements available.")

    # Progress to goal
    st.divider()
    st.header("Goal Progress")

    current = float(latest_weight["value"])
    goal = 100.0
    start = 114.5  # Starting weight
    remaining = current - goal
    progress = ((start - current) / (start - goal)) * 100 if (start - goal) != 0 else 0

    st.progress(min(progress / 100, 1.0))
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Progress", f"{progress:.1f}%")
    with col2:
        st.metric("Remaining", f"{remaining:.1f} kg")
    with col3:
        # Estimate days to goal based on average weekly loss
        if weight_trend["days_tracked"] > 7:
            weeks = weight_trend["days_tracked"] / 7
            avg_weekly = abs(float(weight_trend["change"]) / weeks) if weeks > 0 else 0
            if avg_weekly > 0:
                weeks_to_goal = remaining / avg_weekly
                days_to_goal = int(weeks_to_goal * 7)
                st.metric("Est. Days to Goal", days_to_goal)
            else:
                st.metric("Est. Days to Goal", "N/A")
        else:
            st.metric("Est. Days to Goal", "Need more data")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the FastAPI server is running at http://localhost:8000")
