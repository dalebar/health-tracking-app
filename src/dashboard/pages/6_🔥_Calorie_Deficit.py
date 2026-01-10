"""
Calorie Deficit page - Track TDEE vs Intake for weight loss.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.dashboard.utils.api_client import HealthAPIClient

st.set_page_config(page_title="Calorie Deficit", page_icon="🔥", layout="wide")

st.title("🔥 Calorie Deficit Tracker")
st.markdown("Monitor your energy balance to ensure you're on track for weight loss.")

# Initialize API client
api = HealthAPIClient()

# Date range selector
col1, col2 = st.columns([1, 3])
with col1:
    days = st.selectbox(
        "Time Period",
        options=[7, 14, 21, 30],
        index=0,
        format_func=lambda x: f"Last {x} days",
    )

try:
    # Fetch deficit data
    deficit_data = api.get_calorie_deficit(days=days)
    nutrition_summary = api.get_nutrition_summary(days=days)

    # Check if we have data
    daily_breakdown = deficit_data.get("daily_breakdown", [])

    if not daily_breakdown:
        st.warning("No data available for the selected period.")
        st.stop()

    # Filter to days with complete data
    complete_days = [
        d for d in daily_breakdown if d.get("tdee") and d.get("calories_consumed")
    ]

    if not complete_days:
        st.warning(
            "No complete data (both TDEE and intake) available for the selected period."
        )
        st.info(
            "Make sure you have both Apple Watch activity data and MyFitnessPal logs for the same days."
        )
        st.stop()

    # === SUMMARY METRICS ===
    st.header("📊 Summary")

    avg_deficit = deficit_data.get("avg_deficit")
    avg_tdee = deficit_data.get("avg_tdee")
    avg_intake = deficit_data.get("avg_intake")
    total_deficit = deficit_data.get("total_deficit")

    # Calculate target deficit for 1kg/week loss (7700 kcal = 1kg fat)
    target_daily_deficit = 1100  # ~1.1kg/week for aggressive but achievable loss
    target_weekly_deficit = target_daily_deficit * 7

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if avg_deficit is not None:
            deficit_val = float(avg_deficit)
            on_track = deficit_val >= target_daily_deficit * 0.8  # 80% of target
            st.metric(
                "Avg Daily Deficit",
                f"{deficit_val:,.0f} kcal",
                delta=f"Target: {target_daily_deficit:,} kcal",
                delta_color="normal" if on_track else "inverse",
            )
        else:
            st.metric("Avg Daily Deficit", "--")

    with col2:
        if avg_tdee is not None:
            st.metric(
                "Avg TDEE",
                f"{float(avg_tdee):,.0f} kcal",
                delta="Total Daily Energy Expenditure",
            )
        else:
            st.metric("Avg TDEE", "--")

    with col3:
        if avg_intake is not None:
            st.metric(
                "Avg Intake",
                f"{float(avg_intake):,.0f} kcal",
                delta="Food consumed",
            )
        else:
            st.metric("Avg Intake", "--")

    with col4:
        if total_deficit is not None:
            # Calculate equivalent weight loss
            kg_equivalent = float(total_deficit) / 7700  # 7700 kcal = 1kg fat
            st.metric(
                "Total Deficit",
                f"{float(total_deficit):,.0f} kcal",
                delta=f"≈ {kg_equivalent:.2f} kg fat loss",
            )
        else:
            st.metric("Total Deficit", "--")

    st.divider()

    # === TDEE vs INTAKE CHART ===
    st.header("📈 Daily Energy Balance")

    # Prepare data for chart
    df = pd.DataFrame(complete_days)
    df["date"] = pd.to_datetime(df["date"])
    df["tdee"] = df["tdee"].astype(float)
    df["calories_consumed"] = df["calories_consumed"].astype(float)
    df["deficit"] = df["deficit"].astype(float)
    df["calorie_target"] = df["calorie_target"].apply(lambda x: float(x) if x else None)

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add TDEE bars
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["tdee"],
            name="TDEE (Burned)",
            marker_color="#3498db",
            opacity=0.8,
        ),
        secondary_y=False,
    )

    # Add Intake bars
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["calories_consumed"],
            name="Intake (Consumed)",
            marker_color="#e74c3c",
            opacity=0.8,
        ),
        secondary_y=False,
    )

    # Add target line if available
    if df["calorie_target"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["calorie_target"],
                name="Calorie Target",
                line=dict(color="#2ecc71", width=2, dash="dash"),
            ),
            secondary_y=False,
        )

    # Add cumulative deficit line
    df["cumulative_deficit"] = df["deficit"].cumsum()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["cumulative_deficit"],
            name="Cumulative Deficit",
            line=dict(color="#9b59b6", width=3),
            fill="tozeroy",
            fillcolor="rgba(155, 89, 182, 0.1)",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        barmode="group",
        height=500,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Daily Calories (kcal)", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Deficit (kcal)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

    # === DEFICIT GAUGE ===
    st.header("🎯 Deficit Performance")

    col1, col2 = st.columns(2)

    with col1:
        # Daily deficit gauge
        if avg_deficit is not None:
            deficit_pct = min(float(avg_deficit) / target_daily_deficit * 100, 150)

            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=float(avg_deficit),
                    delta={"reference": target_daily_deficit, "relative": False},
                    title={"text": "Average Daily Deficit"},
                    gauge={
                        "axis": {"range": [0, 1500], "tickwidth": 1},
                        "bar": {"color": "#3498db"},
                        "steps": [
                            {"range": [0, 500], "color": "#ffcccc"},
                            {"range": [500, 800], "color": "#fff3cd"},
                            {"range": [800, 1200], "color": "#d4edda"},
                            {"range": [1200, 1500], "color": "#cce5ff"},
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": target_daily_deficit,
                        },
                    },
                )
            )
            fig_gauge.update_layout(height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        # Progress toward weekly target
        if total_deficit is not None:
            # Projected weekly deficit based on data we have
            days_with_data = len(complete_days)
            projected_weekly = (
                float(total_deficit) / days_with_data * 7 if days_with_data > 0 else 0
            )

            fig_weekly = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=projected_weekly,
                    title={
                        "text": f"Projected Weekly Deficit<br><span style='font-size:0.8em'>({days_with_data} days of data)</span>"
                    },
                    gauge={
                        "axis": {"range": [0, 10000]},
                        "bar": {"color": "#9b59b6"},
                        "steps": [
                            {"range": [0, 3500], "color": "#ffcccc"},  # <0.5kg/week
                            {
                                "range": [3500, 5500],
                                "color": "#fff3cd",
                            },  # 0.5-0.7kg/week
                            {"range": [5500, 7700], "color": "#d4edda"},  # 0.7-1kg/week
                            {"range": [7700, 10000], "color": "#cce5ff"},  # >1kg/week
                        ],
                        "threshold": {
                            "line": {"color": "green", "width": 4},
                            "thickness": 0.75,
                            "value": 7700,  # 1kg fat loss
                        },
                    },
                )
            )
            fig_weekly.add_annotation(
                x=0.5,
                y=-0.15,
                text="Target: 7,700 kcal/week = 1kg fat loss",
                showarrow=False,
                xref="paper",
                yref="paper",
            )
            fig_weekly.update_layout(height=300)
            st.plotly_chart(fig_weekly, use_container_width=True)

    st.divider()

    # === MACRO BREAKDOWN ===
    st.header("🥗 Macro Breakdown")

    if nutrition_summary:
        avg_protein = nutrition_summary.get("avg_protein_g")
        avg_carbs = nutrition_summary.get("avg_carbohydrates_g")
        avg_fat = nutrition_summary.get("avg_fat_g")

        if avg_protein and avg_carbs and avg_fat:
            col1, col2 = st.columns([1, 2])

            with col1:
                # Macro grams
                st.subheader("Daily Averages")
                st.metric("Protein", f"{float(avg_protein):.0f}g", delta="Target: 190g")
                st.metric("Carbs", f"{float(avg_carbs):.0f}g")
                st.metric("Fat", f"{float(avg_fat):.0f}g")

            with col2:
                # Calculate percentages
                protein_cals = float(avg_protein) * 4
                carb_cals = float(avg_carbs) * 4
                fat_cals = float(avg_fat) * 9
                total_macro_cals = protein_cals + carb_cals + fat_cals

                if total_macro_cals > 0:
                    labels = ["Protein", "Carbs", "Fat"]
                    values = [protein_cals, carb_cals, fat_cals]
                    colors = ["#3498db", "#2ecc71", "#e74c3c"]

                    fig_pie = go.Figure(
                        data=[
                            go.Pie(
                                labels=labels,
                                values=values,
                                hole=0.4,
                                marker_colors=colors,
                                textinfo="label+percent",
                                textposition="outside",
                            )
                        ]
                    )

                    fig_pie.update_layout(
                        title="Macro Distribution (by calories)",
                        height=350,
                        showlegend=False,
                    )

                    st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # === DAILY BREAKDOWN TABLE ===
    st.header("📋 Daily Breakdown")

    # Create display dataframe
    display_df = df[
        ["date", "tdee", "calories_consumed", "deficit", "calorie_target"]
    ].copy()
    display_df["date"] = display_df["date"].dt.strftime("%a %d %b")
    display_df.columns = ["Date", "TDEE", "Intake", "Deficit", "Target"]

    # Add status column
    def get_status(row):
        if row["Deficit"] >= target_daily_deficit:
            return "✅ Excellent"
        elif row["Deficit"] >= target_daily_deficit * 0.7:
            return "👍 Good"
        elif row["Deficit"] >= 0:
            return "⚠️ Low"
        else:
            return "❌ Surplus"

    display_df["Status"] = display_df.apply(get_status, axis=1)

    # Format numbers
    for col in ["TDEE", "Intake", "Deficit", "Target"]:
        display_df[col] = display_df[col].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else "--"
        )

    # Display table (newest first)
    st.dataframe(
        display_df.iloc[::-1],
        use_container_width=True,
        hide_index=True,
    )

    # === INSIGHTS ===
    st.header("💡 Insights")

    if avg_deficit is not None:
        deficit_val = float(avg_deficit)

        if deficit_val >= target_daily_deficit:
            st.success(
                f"""
            **🎉 You're on track!** Your average deficit of {deficit_val:,.0f} kcal/day
            exceeds the target of {target_daily_deficit:,} kcal/day.
            At this rate, you'll lose approximately {deficit_val * 7 / 7700:.2f} kg per week.
            """
            )
        elif deficit_val >= target_daily_deficit * 0.7:
            st.info(
                f"""
            **👍 Good progress!** Your average deficit of {deficit_val:,.0f} kcal/day
            is close to the target of {target_daily_deficit:,} kcal/day.
            Consider a slight reduction in intake or increase in activity to hit your goal.
            """
            )
        elif deficit_val >= 0:
            st.warning(
                f"""
            **⚠️ Deficit too low.** Your average deficit of {deficit_val:,.0f} kcal/day
            is below the target of {target_daily_deficit:,} kcal/day.
            To lose 1kg/week, you need to either eat less or move more.
            """
            )
        else:
            st.error(
                f"""
            **❌ Calorie surplus detected.** You're averaging {abs(deficit_val):,.0f} kcal/day
            *above* your TDEE. This will result in weight gain.
            Review your intake and ensure you're logging everything accurately.
            """
            )

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info(
        "Make sure the API server is running and you have nutrition + activity data logged."
    )
    st.exception(e)
