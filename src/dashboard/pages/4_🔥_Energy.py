"""
Energy page - TDEE and activity tracking.
"""

import streamlit as st
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.dashboard.utils.api_client import HealthAPIClient
from src.dashboard.utils.charts import create_tdee_bar_chart

st.set_page_config(page_title="Energy", page_icon="🔥", layout="wide")

st.title("🔥 Energy & Activity")
st.markdown("Track your daily energy expenditure and activity levels.")

# Initialize API client
api = HealthAPIClient()

# Sidebar filters
st.sidebar.header("Date Range")
days_options = {
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90,
}
selected_range = st.sidebar.selectbox(
    "Select range", list(days_options.keys()), index=1
)
days = days_options[selected_range]

today = date.today()
start_date = today - timedelta(days=days)

# Fetch data
try:
    # Activity summary
    activity_summary = api.get_activity_summary(start_date, today)

    # Get daily activity data for chart
    daily_activities = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        try:
            daily_activity = api.get_daily_activity(day)
            daily_activities.append(daily_activity)
        except Exception:  # nosec B110
            # Skip days with no data
            pass

    # Display summary
    st.header("Summary Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_steps = float(activity_summary["avg_steps_per_day"])
        st.metric(
            "Avg Daily Steps",
            f"{avg_steps:.0f}",
            delta=f"{float(activity_summary['total_steps']):.0f} total",
        )

    with col2:
        avg_active = float(activity_summary["avg_active_energy_per_day"])
        st.metric(
            "Avg Active Energy",
            f"{avg_active:.0f} kcal/day",
            delta=f"{float(activity_summary['total_active_energy']):.0f} total",
        )

    with col3:
        avg_exercise = float(activity_summary["avg_exercise_minutes_per_day"])
        st.metric(
            "Avg Exercise Time",
            f"{avg_exercise:.0f} min/day",
            delta=f"{float(activity_summary['total_exercise_minutes']):.0f} total",
        )

    with col4:
        # Calculate average TDEE if we have data
        if daily_activities:
            tdees = [
                float(d.get("total_energy_kcal", 0))
                for d in daily_activities
                if d.get("total_energy_kcal")
            ]
            avg_tdee = sum(tdees) / len(tdees) if tdees else 0
            st.metric("Avg TDEE", f"{avg_tdee:.0f} kcal/day")
        else:
            st.metric("Avg TDEE", "N/A")

    st.divider()

    # TDEE Chart
    st.header("Total Daily Energy Expenditure (TDEE)")

    if daily_activities:
        fig = create_tdee_bar_chart(daily_activities)
        st.plotly_chart(fig, use_container_width=True)

        st.info(
            "💡 **TDEE** = Resting Energy (BMR) + Active Energy. This represents your total calories burned per day."
        )
    else:
        st.info("No energy data available for the selected period.")

    st.divider()

    # Activity details
    st.header("Daily Activity Details")

    if daily_activities:
        activity_data = []
        for d in reversed(daily_activities):  # Show newest first
            activity_data.append(
                {
                    "Date": d["date"],
                    "Steps": (
                        f"{float(d.get('steps', 0)):.0f}" if d.get("steps") else "N/A"
                    ),
                    "Active Energy (kcal)": (
                        f"{float(d.get('active_energy_kcal', 0)):.0f}"
                        if d.get("active_energy_kcal")
                        else "N/A"
                    ),
                    "Resting Energy (kcal)": (
                        f"{float(d.get('resting_energy_kcal', 0)):.0f}"
                        if d.get("resting_energy_kcal")
                        else "N/A"
                    ),
                    "TDEE (kcal)": (
                        f"{float(d.get('total_energy_kcal', 0)):.0f}"
                        if d.get("total_energy_kcal")
                        else "N/A"
                    ),
                    "Exercise (min)": (
                        f"{float(d.get('exercise_minutes', 0)):.0f}"
                        if d.get("exercise_minutes")
                        else "N/A"
                    ),
                }
            )

        st.dataframe(activity_data, use_container_width=True)
    else:
        st.info("No daily activity data available.")

    st.divider()

    # Insights
    st.header("Activity Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Steps Analysis")
        avg_steps = float(activity_summary["avg_steps_per_day"])

        if avg_steps >= 10000:
            st.success(
                f"🎉 Excellent! You're averaging {avg_steps:.0f} steps per day, exceeding the recommended 10,000 steps!"
            )
        elif avg_steps >= 7500:
            st.info(
                f"👍 Good! You're averaging {avg_steps:.0f} steps per day. Try to reach 10,000 for optimal health."
            )
        else:
            st.warning(
                f"You're averaging {avg_steps:.0f} steps per day. Consider increasing daily movement to reach 10,000 steps."
            )

    with col2:
        st.subheader("Exercise Time")
        avg_exercise = float(activity_summary["avg_exercise_minutes_per_day"])

        if avg_exercise >= 30:
            st.success(
                f"💪 Great! You're exercising {avg_exercise:.0f} minutes per day on average!"
            )
        elif avg_exercise >= 20:
            st.info(
                f"Good effort! {avg_exercise:.0f} minutes per day. Aim for 30+ for optimal health."
            )
        else:
            st.warning(
                f"Currently averaging {avg_exercise:.0f} minutes per day. Try to reach 30 minutes of daily exercise."
            )

    # Energy balance info
    st.divider()
    st.header("Understanding Energy Metrics")

    with st.expander("What is TDEE?"):
        st.markdown(
            """
        **Total Daily Energy Expenditure (TDEE)** is the total number of calories you burn in a day.

        It consists of:
        - **Resting Energy (BMR)**: Calories burned at rest (60-75% of TDEE)
        - **Active Energy**: Calories burned through activity and exercise (25-40% of TDEE)

        For weight loss, you need to maintain a calorie deficit (consume fewer calories than your TDEE).
        """
        )

    with st.expander("How many steps should I aim for?"):
        st.markdown(
            """
        **Step Goals:**
        - **10,000 steps/day**: General health recommendation
        - **7,500 steps/day**: Moderate activity level
        - **5,000 steps/day**: Sedentary lifestyle

        Benefits of 10,000 steps:
        - Improved cardiovascular health
        - Better weight management
        - Enhanced mood and energy levels
        - Reduced risk of chronic diseases
        """
        )

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure the FastAPI server is running at http://localhost:8000")
