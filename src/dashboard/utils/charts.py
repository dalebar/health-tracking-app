"""
Reusable chart components using Plotly.
"""

import plotly.graph_objects as go
import plotly.express as px


def create_weight_trend_chart(
    measurements: list, goal_weight: float = 100.0
) -> go.Figure:
    """
    Create weight trend line chart with goal line.

    Args:
        measurements: List of weight measurements with 'recorded_at' and 'value'
        goal_weight: Target weight in kg
    """
    dates = [m["recorded_at"].split("T")[0] for m in measurements]
    weights = [float(m["value"]) for m in measurements]

    fig = go.Figure()

    # Weight line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=weights,
            mode="lines+markers",
            name="Weight",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=6),
        )
    )

    # Goal line
    fig.add_trace(
        go.Scatter(
            x=[dates[0], dates[-1]],
            y=[goal_weight, goal_weight],
            mode="lines",
            name="Goal (100 kg)",
            line=dict(color="#2ca02c", width=2, dash="dash"),
        )
    )

    fig.update_layout(
        title="Weight Progress",
        xaxis_title="Date",
        yaxis_title="Weight (kg)",
        hovermode="x unified",
        template="plotly_white",
    )

    return fig


def create_workout_pie_chart(stats: list) -> go.Figure:
    """
    Create pie chart showing workout type distribution.

    Args:
        stats: List of workout stats with 'workout_type' and 'count'
    """
    types = [s["workout_type"] for s in stats]
    counts = [s["count"] for s in stats]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=types,
                values=counts,
                hole=0.3,  # Donut chart
                marker=dict(colors=px.colors.qualitative.Set3),
            )
        ]
    )

    fig.update_layout(
        title="Workout Type Distribution",
        template="plotly_white",
    )

    return fig


def create_tdee_bar_chart(activity_data: list) -> go.Figure:
    """
    Create stacked bar chart for TDEE (active + resting energy).

    Args:
        activity_data: List of daily activity with dates and energy values
    """
    dates = [d["date"] for d in activity_data]
    active = [float(d.get("active_energy_kcal", 0)) for d in activity_data]
    resting = [float(d.get("resting_energy_kcal", 0)) for d in activity_data]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=dates,
            y=resting,
            name="Resting Energy (BMR)",
            marker_color="lightblue",
        )
    )

    fig.add_trace(
        go.Bar(
            x=dates,
            y=active,
            name="Active Energy",
            marker_color="orange",
        )
    )

    fig.update_layout(
        title="Total Daily Energy Expenditure (TDEE)",
        xaxis_title="Date",
        yaxis_title="Energy (kcal)",
        barmode="stack",
        hovermode="x unified",
        template="plotly_white",
    )

    return fig


def create_boxing_performance_chart(workouts: list) -> go.Figure:
    """
    Create line chart showing boxing performance over time.

    Args:
        workouts: List of boxing workouts with dates, calories, and HR
    """
    dates = [w["start_time"].split("T")[0] for w in workouts]
    calories = [float(w.get("total_energy_kcal", 0)) for w in workouts]
    hr = [w.get("avg_heart_rate_bpm") for w in workouts]

    fig = go.Figure()

    # Calories
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=calories,
            mode="lines+markers",
            name="Calories",
            yaxis="y",
            line=dict(color="red", width=2),
        )
    )

    # Heart Rate (dual axis)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=hr,
            mode="lines+markers",
            name="Avg Heart Rate",
            yaxis="y2",
            line=dict(color="blue", width=2),
        )
    )

    fig.update_layout(
        title="Boxing Performance Over Time",
        xaxis_title="Date",
        yaxis=dict(title="Calories (kcal)", side="left"),
        yaxis2=dict(title="Heart Rate (bpm)", side="right", overlaying="y"),
        hovermode="x unified",
        template="plotly_white",
    )

    return fig
