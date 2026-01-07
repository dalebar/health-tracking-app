"""
Recovery page - Sleep and heart rate analysis.
"""

import streamlit as st
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.dashboard.utils.api_client import HealthAPIClient

st.set_page_config(page_title="Recovery", page_icon="😴", layout="wide")

st.title("😴 Recovery & Health Metrics")
st.markdown("Monitor your sleep, heart rate, and recovery indicators.")

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
    "Select range", list(days_options.keys()), index=0
)
days = days_options[selected_range]

today = date.today()
start_date = today - timedelta(days=days)

st.info(
    """
⚠️ **Note**: Sleep and advanced heart rate metrics require additional API endpoints.

This page demonstrates the dashboard structure. To fully populate this page, implement:
- Sleep session endpoints (duration, quality, deep/REM sleep)
- Resting heart rate endpoints
- Heart rate variability (HRV) endpoints
- VO2 max endpoints

These metrics are available in your database and can be exposed via FastAPI routes similar to the existing body/activity/workout endpoints.
"""
)

st.divider()

# Placeholder metrics
st.header("Recovery Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Avg Sleep", "7h 24m", delta="+12m vs last week")

with col2:
    st.metric("Resting HR", "62 bpm", delta="-2 bpm")

with col3:
    st.metric("HRV", "45 ms", delta="+3 ms")

with col4:
    st.metric("VO2 Max", "42 ml/kg/min", delta="+1")

st.divider()

# Implementation guide
st.header("Implementation Guide")

st.markdown(
    """
### To complete this page, add these API endpoints:

#### 1. Sleep Data
```python
# In src/api/routes/recovery.py

@router.get("/sleep/history")
def get_sleep_history(start_date: date, end_date: date, db: Session):
    # Query SleepSession table
    # Return: date, duration, sleep_score, deep_sleep_minutes, rem_sleep_minutes
    pass

@router.get("/sleep/summary")
def get_sleep_summary(days: int, db: Session):
    # Return aggregated sleep stats
    pass
```

#### 2. Heart Rate Data
```python
@router.get("/heart-rate/resting")
def get_resting_heart_rate(start_date: date, end_date: date, db: Session):
    # Query HealthMetric table for resting_heart_rate
    pass

@router.get("/heart-rate/hrv")
def get_hrv(start_date: date, end_date: date, db: Session):
    # Query HealthMetric table for heart_rate_variability
    pass

@router.get("/fitness/vo2-max")
def get_vo2_max(start_date: date, end_date: date, db: Session):
    # Query HealthMetric table for vo2_max
    pass
```

#### 3. Update API Client
Add these methods to `src/dashboard/utils/api_client.py`:
```python
def get_sleep_history(self, start_date: date, end_date: date) -> dict:
    # Fetch sleep data
    pass

def get_resting_heart_rate(self, start_date: date, end_date: date) -> dict:
    # Fetch resting HR
    pass
```

#### 4. Create Charts
Add to `src/dashboard/utils/charts.py`:
```python
def create_sleep_trend_chart(sleep_data: list) -> go.Figure:
    # Line chart for sleep duration over time
    pass

def create_hrv_chart(hrv_data: list) -> go.Figure:
    # Line chart for HRV trends
    pass
```
"""
)

st.divider()

# Example visualization placeholders
st.header("Example Visualizations")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Sleep Duration")
    st.line_chart({"Hours": [7.2, 6.8, 7.5, 7.8, 7.1, 7.4, 7.6]})
    st.caption("Example: Sleep hours per night over the last week")

with col2:
    st.subheader("Resting Heart Rate")
    st.line_chart({"BPM": [64, 63, 62, 63, 61, 62, 62]})
    st.caption("Example: Resting heart rate trend")

st.divider()

st.header("Recovery Insights")

st.markdown(
    """
### Key Recovery Metrics:

**Sleep**
- Adults need 7-9 hours of quality sleep per night
- Deep sleep (20-25% of total) is crucial for physical recovery
- REM sleep (20-25% of total) supports mental recovery

**Resting Heart Rate**
- Lower resting HR indicates better cardiovascular fitness
- Track trends over time rather than single measurements
- Elevated RHR may indicate stress, illness, or overtraining

**Heart Rate Variability (HRV)**
- Higher HRV generally indicates better recovery
- Low HRV may signal need for rest
- Training adaptations improve HRV over time

**VO2 Max**
- Measures cardiovascular fitness capacity
- Higher values indicate better aerobic fitness
- Improves with consistent cardio training
"""
)

st.info(
    """
💡 **Next Steps**:
1. Create the recovery API endpoints in FastAPI
2. Update the API client with new methods
3. Replace placeholder data with real API calls
4. Add interactive charts for sleep and HR trends
"""
)

# Show that we can still get workout data (which includes HR)
st.divider()
st.header("Workout Heart Rate Data")

try:
    workouts = api.list_workouts(start_date=start_date, end_date=today, limit=50)

    if workouts["workouts"]:
        hr_data = []
        for w in workouts["workouts"]:
            if w.get("avg_heart_rate_bpm"):
                hr_data.append(
                    {
                        "Date": w["start_time"].split("T")[0],
                        "Workout": w["workout_type"],
                        "Avg HR": w["avg_heart_rate_bpm"],
                        "Min HR": w.get("min_heart_rate_bpm", "N/A"),
                        "Max HR": w.get("max_heart_rate_bpm", "N/A"),
                    }
                )

        if hr_data:
            st.dataframe(hr_data, use_container_width=True)
            st.caption("Heart rate data from recent workouts")
        else:
            st.info("No heart rate data available in recent workouts")
    else:
        st.info("No workout data available for the selected period")

except Exception as e:
    st.error(f"Error loading workout data: {e}")
