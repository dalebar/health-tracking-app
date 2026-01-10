"""
Health Tracking Dashboard - Main Application.

Multi-page Streamlit app for visualizing health metrics.
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.dashboard.utils.api_client import HealthAPIClient

# Page config
st.set_page_config(
    page_title="Health Tracking Dashboard",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title and description
st.title("💪 Health Tracking Dashboard")
st.markdown(
    """
Track your health transformation journey with comprehensive metrics and visualizations.
Navigate using the sidebar to explore different aspects of your health data.
"""
)

# Sidebar info
with st.sidebar:
    st.header("About")
    st.markdown(
        """
    **Phase 3B Dashboard**

    Built with:
    - Streamlit
    - FastAPI
    - Plotly
    - PostgreSQL

    Navigate to different pages using the menu above.
    """
    )

    st.divider()

    st.markdown(
        """
    **Quick Stats:**
    - 🎯 Goal: 100 kg by April 2026
    - 🥊 167 Boxing Sessions
    - 📊 1.6M+ Health Records
    - 💾 PostgreSQL Database
    """
    )

# Initialize API client
api = HealthAPIClient()

# Main page content
st.header("Welcome! 👋")

# Fetch live data
try:
    latest_weight = api.get_latest_weight()
    weight_trend = api.get_weight_trend(days=7)

    current_weight = float(latest_weight["value"])
    week_change = float(weight_trend["change"])
    goal_weight = 100.0
    start_weight = 114.5
    remaining = current_weight - goal_weight

    # Calculate days to goal based on current rate
    days_to_goal: int | None = None
    if week_change < 0:  # Losing weight
        weekly_rate = abs(week_change)
        weeks_to_goal = remaining / weekly_rate if weekly_rate > 0 else 999
        days_to_goal = int(weeks_to_goal * 7)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Current Weight",
            value=f"{current_weight:.1f} kg",
            delta=f"{week_change:+.1f} kg this week",
            delta_color="inverse",
        )

    with col2:
        st.metric(
            label="Goal Weight",
            value=f"{goal_weight:.0f} kg",
            delta=f"{remaining:.1f} kg to go",
        )

    with col3:
        if days_to_goal and days_to_goal < 365:
            st.metric(
                label="Days to Goal",
                value=f"~{days_to_goal} days",
                delta="At current pace",
            )
        else:
            st.metric(
                label="Days to Goal",
                value="--",
                delta="Need deficit to calculate",
            )

except Exception:
    # Fallback to static display if API unavailable
    st.warning("⏳ Connecting to API... (may take 30s on cold start)")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Current Weight", value="--", delta="Loading...")
    with col2:
        st.metric(label="Goal Weight", value="100 kg", delta="--")
    with col3:
        st.metric(label="Days to Goal", value="--", delta="--")

st.divider()

st.subheader("📊 What's Available")

st.markdown(
    """
### Pages:

1. **📊 Overview** - Weekly summary and key metrics
2. **⚖️ Weight** - Weight loss progress and trends
3. **🥊 Workouts** - Training history and performance
4. **🔥 Energy** - TDEE and activity tracking
5. **😴 Recovery** - Sleep and heart rate analysis

### Getting Started:

Use the **sidebar menu** to navigate between pages. Each page provides:
- Interactive charts
- Date range filtering
- Detailed metrics
- Download options

**🚀 Your data is live!** All metrics are pulled from your FastAPI backend.
"""
)

st.info(
    "💡 **Tip:** Start with the Overview page for a quick summary of your progress!"
)
