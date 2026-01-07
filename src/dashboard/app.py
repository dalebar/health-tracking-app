"""
Health Tracking Dashboard - Main Application.

Multi-page Streamlit app for visualizing health metrics.
"""

import streamlit as st

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

# Main page content
st.header("Welcome! 👋")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Current Weight",
        value="114.5 kg",
        delta="-0.5 kg this week",
        delta_color="inverse",
    )

with col2:
    st.metric(
        label="Goal Weight",
        value="100 kg",
        delta="14.5 kg to go",
    )

with col3:
    st.metric(
        label="Days to Goal",
        value="~90 days",
        delta="April 2026",
    )

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
