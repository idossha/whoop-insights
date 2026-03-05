import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import os
from src.whoop_sync.mlr import (
    prepare_recovery_mlr_data,
    prepare_hrv_mlr_data,
    fit_recovery_ridge_model,
    fit_hrv_ridge_model,
)

st.set_page_config(page_title="Whoop Dashboard", layout="wide")

st.title("Whoop Dashboard")

DB_PATH = os.getenv("WHOOP_DB_PATH", "whoop.db")


@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_data():
    conn = get_connection()

    cycles = pd.read_sql("SELECT * FROM cycles ORDER BY start DESC", conn)
    recoveries = pd.read_sql("SELECT * FROM recoveries ORDER BY updated_at DESC", conn)
    sleeps = pd.read_sql("SELECT * FROM sleeps ORDER BY start DESC", conn)
    workouts = pd.read_sql("SELECT * FROM workouts ORDER BY start DESC", conn)
    profile = pd.read_sql("SELECT * FROM user_profile", conn)
    body = pd.read_sql("SELECT * FROM body_measurement", conn)

    return cycles, recoveries, sleeps, workouts, profile, body


def parse_datetime(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col].str.replace("Z", "+00:00"), utc=True)
    return df


cycles, recoveries, sleeps, workouts, profile, body = load_data()

if cycles.empty:
    st.warning("No data found. Run `python main.py sync` to fetch your data.")
    st.stop()

cycles = parse_datetime(cycles, ["start", "end", "created_at", "updated_at"])
sleeps = parse_datetime(sleeps, ["start", "end", "created_at", "updated_at"])
workouts = parse_datetime(workouts, ["start", "end", "created_at", "updated_at"])
recoveries["updated_at"] = pd.to_datetime(
    recoveries["updated_at"].str.replace("Z", "+00:00"), utc=True
)

cycles["date"] = cycles["start"].dt.date
sleeps["date"] = sleeps["start"].dt.date
workouts["date"] = workouts["start"].dt.date

min_date = cycles["date"].min()
max_date = cycles["date"].max()

default_start = max(min_date, max_date - timedelta(days=30))

st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Date Range",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = date_range[0]
    end_date = max_date

cycles_filtered = cycles[(cycles["date"] >= start_date) & (cycles["date"] <= end_date)]
recoveries_filtered = recoveries[recoveries["cycle_id"].isin(cycles_filtered["id"])]
sleeps_filtered = sleeps[(sleeps["date"] >= start_date) & (sleeps["date"] <= end_date)]
workouts_filtered = workouts[
    (workouts["date"] >= start_date) & (workouts["date"] <= end_date)
]

if not profile.empty:
    st.sidebar.markdown(
        f"### {profile.iloc[0]['first_name']} {profile.iloc[0]['last_name']}"
    )

if not body.empty:
    b = body.iloc[0]
    st.sidebar.markdown(f"**Height:** {b['height_meter']:.2f}m")
    st.sidebar.markdown(f"**Weight:** {b['weight_kilogram']:.1f}kg")
    st.sidebar.markdown(f"**Max HR:** {b['max_heart_rate']} bpm")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Data Range:** {min_date} to {max_date}")
st.sidebar.markdown(f"**Total Cycles:** {len(cycles)}")
st.sidebar.markdown(f"**Total Workouts:** {len(workouts)}")

st.header("Overview")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    avg_recovery = recoveries_filtered["recovery_score"].mean()
    st.metric(
        "Avg Recovery", f"{avg_recovery:.0f}%" if pd.notna(avg_recovery) else "N/A"
    )

with col2:
    avg_strain = cycles_filtered["strain"].mean()
    st.metric("Avg Strain", f"{avg_strain:.1f}" if pd.notna(avg_strain) else "N/A")

with col3:
    avg_sleep = sleeps_filtered["sleep_performance_percentage"].mean()
    st.metric("Avg Sleep Perf", f"{avg_sleep:.0f}%" if pd.notna(avg_sleep) else "N/A")

with col4:
    workout_count = len(workouts_filtered)
    st.metric("Workouts", workout_count)

with col5:
    avg_rhr = recoveries_filtered["resting_heart_rate"].mean()
    st.metric("Avg RHR", f"{avg_rhr:.0f} bpm" if pd.notna(avg_rhr) else "N/A")

with col6:
    avg_hrv = recoveries_filtered["hrv_rmssd_milli"].mean()
    st.metric("Avg HRV", f"{avg_hrv:.1f} ms" if pd.notna(avg_hrv) else "N/A")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "Recovery & Strain",
        "Sleep",
        "Heart Rate",
        "Workouts",
        "Insights",
        "MLR Recovery",
        "MLR HRV",
    ]
)

with tab1:
    df_merged = (
        cycles_filtered[["date", "strain", "id"]]
        .merge(
            recoveries_filtered[
                ["cycle_id", "recovery_score", "resting_heart_rate", "hrv_rmssd_milli"]
            ],
            left_on="id",
            right_on="cycle_id",
            how="left",
        )
        .sort_values("date")
    )

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Recovery Score", "Strain"),
        vertical_spacing=0.15,
    )

    fig.add_trace(
        go.Bar(
            x=df_merged["date"],
            y=df_merged["recovery_score"],
            name="Recovery",
            marker_color="#00D4AA",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=df_merged["date"],
            y=df_merged["strain"],
            name="Strain",
            marker_color="#FF6B6B",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(height=500, showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
    fig.update_xaxes(title_text="Date", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    sleep_df = sleeps_filtered.sort_values("date")

    sleep_df["light_hrs"] = sleep_df["total_light_sleep_time_milli"] / 3600000
    sleep_df["deep_hrs"] = sleep_df["total_slow_wave_sleep_time_milli"] / 3600000
    sleep_df["rem_hrs"] = sleep_df["total_rem_sleep_time_milli"] / 3600000
    sleep_df["awake_hrs"] = sleep_df["total_awake_time_milli"] / 3600000
    sleep_df["total_sleep_hrs"] = (
        sleep_df["light_hrs"] + sleep_df["deep_hrs"] + sleep_df["rem_hrs"]
    )

    st.subheader("Sleep Stages Breakdown")

    fig_stages = go.Figure()
    fig_stages.add_trace(
        go.Bar(
            x=sleep_df["date"],
            y=sleep_df["awake_hrs"],
            name="Awake",
            marker_color="#E74C3C",
        )
    )
    fig_stages.add_trace(
        go.Bar(
            x=sleep_df["date"],
            y=sleep_df["light_hrs"],
            name="Light Sleep",
            marker_color="#85C1E9",
        )
    )
    fig_stages.add_trace(
        go.Bar(
            x=sleep_df["date"],
            y=sleep_df["deep_hrs"],
            name="Deep Sleep",
            marker_color="#2E86AB",
        )
    )
    fig_stages.add_trace(
        go.Bar(
            x=sleep_df["date"],
            y=sleep_df["rem_hrs"],
            name="REM Sleep",
            marker_color="#A569BD",
        )
    )

    fig_stages.update_layout(
        barmode="stack",
        xaxis_title="Date",
        yaxis_title="Hours",
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_stages, use_container_width=True)

    st.subheader("Sleep Performance & Efficiency Trend")

    fig_perf = go.Figure()
    fig_perf.add_trace(
        go.Scatter(
            x=sleep_df["date"],
            y=sleep_df["sleep_performance_percentage"],
            name="Sleep Performance",
            mode="lines+markers",
            line_color="#3498DB",
        )
    )
    fig_perf.add_trace(
        go.Scatter(
            x=sleep_df["date"],
            y=sleep_df["sleep_efficiency_percentage"],
            name="Sleep Efficiency",
            mode="lines+markers",
            line_color="#27AE60",
        )
    )

    fig_perf.update_layout(
        xaxis_title="Date",
        yaxis_title="Percentage",
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_perf, use_container_width=True)

with tab3:
    df_hr_base = cycles_filtered[
        ["date", "average_heart_rate", "max_heart_rate", "id"]
    ].sort_values("date")
    df_recovery_hr = recoveries_filtered[
        ["cycle_id", "resting_heart_rate", "hrv_rmssd_milli"]
    ]
    df_hr = df_hr_base.merge(
        df_recovery_hr, left_on="id", right_on="cycle_id", how="left"
    )

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Heart Rate (BPM)", "HRV (ms)"),
        vertical_spacing=0.15,
    )

    fig.add_trace(
        go.Scatter(
            x=df_hr["date"],
            y=df_hr["average_heart_rate"],
            name="Avg HR (Daily)",
            mode="lines+markers",
            line_color="#E74C3C",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_hr["date"],
            y=df_hr["max_heart_rate"],
            name="Max HR (Daily)",
            mode="lines+markers",
            line_color="#C0392B",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_hr["date"],
            y=df_hr["resting_heart_rate"],
            name="RHR (Resting)",
            mode="lines+markers",
            line_color="#3498DB",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df_hr["date"],
            y=df_hr["hrv_rmssd_milli"],
            name="HRV",
            mode="lines+markers",
            line_color="#9B59B6",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(height=600, margin=dict(l=0, r=0, t=30, b=0))
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="BPM", row=1, col=1)
    fig.update_yaxes(title_text="ms", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    if not workouts_filtered.empty:
        st.subheader("Workout History")

        workout_df = workouts_filtered.copy()
        workout_df["duration_min"] = (
            workout_df["end"] - workout_df["start"]
        ).dt.total_seconds() / 60

        col1, col2 = st.columns(2)
        with col1:
            sport_counts = workout_df["sport_name"].value_counts()
            fig = px.pie(
                values=sport_counts.values,
                names=sport_counts.index,
                title="Workouts by Type",
            )
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.scatter(
                workout_df,
                x="date",
                y="strain",
                color="sport_name",
                size="duration_min",
                title="Workout Strain by Date",
                hover_data=["average_heart_rate"],
            )
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent Workouts")
        display_cols = [
            "date",
            "sport_name",
            "strain",
            "average_heart_rate",
            "max_heart_rate",
            "duration_min",
        ]
        workout_display = (
            workout_df[display_cols].sort_values("date", ascending=False).head(10)
        )
        workout_display.columns = [
            "Date",
            "Sport",
            "Strain",
            "Avg HR",
            "Max HR",
            "Duration (min)",
        ]
        st.dataframe(workout_display, use_container_width=True, hide_index=True)
    else:
        st.info("No workouts in selected date range.")

with tab5:
    st.subheader("Data Correlations & Insights")

    df_insights = (
        cycles_filtered[["date", "strain", "id", "kilojoule"]]
        .merge(
            recoveries_filtered[
                ["cycle_id", "recovery_score", "resting_heart_rate", "hrv_rmssd_milli"]
            ],
            left_on="id",
            right_on="cycle_id",
            how="left",
        )
        .merge(
            sleeps_filtered[
                [
                    "cycle_id",
                    "sleep_performance_percentage",
                    "sleep_efficiency_percentage",
                    "total_light_sleep_time_milli",
                    "total_slow_wave_sleep_time_milli",
                    "total_rem_sleep_time_milli",
                    "total_awake_time_milli",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="left",
        )
    )

    df_insights["sleep_hrs"] = (
        df_insights["total_light_sleep_time_milli"].fillna(0)
        + df_insights["total_slow_wave_sleep_time_milli"].fillna(0)
        + df_insights["total_rem_sleep_time_milli"].fillna(0)
    ) / 3600000

    df_insights["deep_sleep_hrs"] = (
        df_insights["total_slow_wave_sleep_time_milli"] / 3600000
    )
    df_insights["rem_sleep_hrs"] = df_insights["total_rem_sleep_time_milli"] / 3600000
    df_insights["awake_min"] = df_insights["total_awake_time_milli"] / 60000

    st.markdown("### Correlation Matrix")
    corr_cols = [
        "recovery_score",
        "strain",
        "hrv_rmssd_milli",
        "resting_heart_rate",
        "sleep_performance_percentage",
        "sleep_hrs",
        "deep_sleep_hrs",
    ]
    corr_df = df_insights[corr_cols].corr()
    corr_df.columns = [
        "Recovery",
        "Strain",
        "HRV",
        "RHR",
        "Sleep Perf",
        "Sleep Hrs",
        "Deep Sleep",
    ]
    corr_df.index = corr_df.columns

    fig_corr = px.imshow(
        corr_df,
        color_continuous_scale="RdBu_r",
        aspect="auto",
        title="Feature Correlations",
    )
    fig_corr.update_layout(height=500, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("### Key Relationships")

    def _add_ols_line(fig, x_vals, y_vals):
        mask = np.isfinite(x_vals) & np.isfinite(y_vals)
        if mask.sum() > 1:
            x_clean, y_clean = x_vals[mask], y_vals[mask]
            coeffs = np.polyfit(x_clean, y_clean, 1)
            x_sorted = np.sort(x_clean)
            fig.add_trace(
                go.Scatter(
                    x=x_sorted,
                    y=np.polyval(coeffs, x_sorted),
                    mode="lines",
                    line=dict(dash="dash", width=2),
                    name="Trend",
                    showlegend=False,
                )
            )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Sleep vs Next Day Recovery")
        fig_sleep_rec = go.Figure()
        fig_sleep_rec.add_trace(
            go.Scatter(
                x=df_insights["sleep_hrs"],
                y=df_insights["recovery_score"],
                mode="markers",
                marker=dict(opacity=0.7),
                name="Data",
            )
        )
        _add_ols_line(fig_sleep_rec, df_insights["sleep_hrs"].values, df_insights["recovery_score"].values)
        fig_sleep_rec.update_layout(
            title="Sleep Hours vs Recovery Score",
            xaxis_title="Sleep (hours)",
            yaxis_title="Recovery (%)",
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig_sleep_rec, use_container_width=True)

        if df_insights["sleep_hrs"].notna().sum() > 2:
            corr_val = df_insights["sleep_hrs"].corr(df_insights["recovery_score"])
            st.info(f"Correlation: **{corr_val:.2f}**")

    with col2:
        st.markdown("#### HRV vs Recovery")
        fig_hrv_rec = go.Figure()
        fig_hrv_rec.add_trace(
            go.Scatter(
                x=df_insights["hrv_rmssd_milli"],
                y=df_insights["recovery_score"],
                mode="markers",
                marker=dict(color="#9B59B6", opacity=0.7),
                name="Data",
            )
        )
        _add_ols_line(fig_hrv_rec, df_insights["hrv_rmssd_milli"].values, df_insights["recovery_score"].values)
        fig_hrv_rec.update_layout(
            title="HRV vs Recovery Score",
            xaxis_title="HRV (ms)",
            yaxis_title="Recovery (%)",
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig_hrv_rec, use_container_width=True)

        if df_insights["hrv_rmssd_milli"].notna().sum() > 2:
            corr_val = df_insights["hrv_rmssd_milli"].corr(
                df_insights["recovery_score"]
            )
            st.info(f"Correlation: **{corr_val:.2f}**")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Strain vs RHR")
        fig_strain_rhr = go.Figure()
        fig_strain_rhr.add_trace(
            go.Scatter(
                x=df_insights["strain"],
                y=df_insights["resting_heart_rate"],
                mode="markers",
                marker=dict(color="#E74C3C", opacity=0.7),
                name="Data",
            )
        )
        _add_ols_line(fig_strain_rhr, df_insights["strain"].values, df_insights["resting_heart_rate"].values)
        fig_strain_rhr.update_layout(
            title="Daily Strain vs Resting HR",
            xaxis_title="Strain",
            yaxis_title="RHR (bpm)",
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig_strain_rhr, use_container_width=True)

        if df_insights["strain"].notna().sum() > 2:
            corr_val = df_insights["strain"].corr(df_insights["resting_heart_rate"])
            st.info(f"Correlation: **{corr_val:.2f}**")

    with col4:
        st.markdown("#### Deep Sleep vs Recovery")
        fig_deep_rec = go.Figure()
        fig_deep_rec.add_trace(
            go.Scatter(
                x=df_insights["deep_sleep_hrs"],
                y=df_insights["recovery_score"],
                mode="markers",
                marker=dict(color="#2E86AB", opacity=0.7),
                name="Data",
            )
        )
        _add_ols_line(fig_deep_rec, df_insights["deep_sleep_hrs"].values, df_insights["recovery_score"].values)
        fig_deep_rec.update_layout(
            title="Deep Sleep vs Recovery",
            xaxis_title="Deep Sleep (hrs)",
            yaxis_title="Recovery (%)",
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig_deep_rec, use_container_width=True)

        if df_insights["deep_sleep_hrs"].notna().sum() > 2:
            corr_val = df_insights["deep_sleep_hrs"].corr(df_insights["recovery_score"])
            st.info(f"Correlation: **{corr_val:.2f}**")

    st.markdown("---")
    st.markdown("### Statistical Summary")

    col5, col6 = st.columns(2)
    with col5:
        st.markdown("#### Best Recovery Days")
        best_days = df_insights.nlargest(5, "recovery_score")[
            ["date", "recovery_score", "sleep_hrs", "hrv_rmssd_milli"]
        ]
        best_days.columns = ["Date", "Recovery", "Sleep Hrs", "HRV"]
        st.dataframe(best_days, hide_index=True, use_container_width=True)

    with col6:
        st.markdown("#### Worst Recovery Days")
        worst_days = df_insights.nsmallest(5, "recovery_score")[
            ["date", "recovery_score", "sleep_hrs", "hrv_rmssd_milli"]
        ]
        worst_days.columns = ["Date", "Recovery", "Sleep Hrs", "HRV"]
        st.dataframe(worst_days, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("### Workout Impact Analysis")

    if not workouts_filtered.empty:
        workout_dates = set(workouts_filtered["date"])
        df_insights["had_workout"] = df_insights["date"].isin(workout_dates)

        workout_days = df_insights[df_insights["had_workout"]]
        rest_days = df_insights[~df_insights["had_workout"]]

        col7, col8, col9 = st.columns(3)

        with col7:
            if len(workout_days) > 0 and len(rest_days) > 0:
                avg_strain_w = workout_days["strain"].mean()
                avg_strain_r = rest_days["strain"].mean()
                st.metric(
                    "Avg Strain (Workout Days)",
                    f"{avg_strain_w:.1f}",
                    f"{avg_strain_w - avg_strain_r:+.1f} vs rest",
                )

        with col8:
            if len(workout_days) > 0 and len(rest_days) > 0:
                avg_hrv_w = workout_days["hrv_rmssd_milli"].mean()
                avg_hrv_r = rest_days["hrv_rmssd_milli"].mean()
                st.metric(
                    "Avg HRV (Workout Days)",
                    f"{avg_hrv_w:.1f} ms",
                    f"{avg_hrv_w - avg_hrv_r:+.1f} vs rest",
                )

        with col9:
            if len(workout_days) > 0 and len(rest_days) > 0:
                avg_rec_w = workout_days["recovery_score"].mean()
                avg_rec_r = rest_days["recovery_score"].mean()
                st.metric(
                    "Avg Recovery (Workout Days)",
                    f"{avg_rec_w:.0f}%",
                    f"{avg_rec_w - avg_rec_r:+.0f}% vs rest",
                )
    else:
        st.info("Not enough workout data for impact analysis.")

with tab6:
    st.subheader("Ridge Regression: Predicting Recovery")

    st.markdown("""
    This model predicts **Recovery Score** using Ridge regression with standardized features.
    The timeline below shows how well the model tracks actual recovery over time.
    """)

    df_mlr = prepare_recovery_mlr_data(
        cycles_filtered, recoveries_filtered, sleeps_filtered, workouts_filtered
    )

    ridge_rec = fit_recovery_ridge_model(df_mlr)

    if ridge_rec is None:
        st.warning("Not enough data for Ridge model. Need at least 10 complete observations.")
    else:
        # Model stats
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("R²", f"{ridge_rec['r2']:.3f}")
        with col_m2:
            st.metric("MAE", f"{ridge_rec['mae']:.2f}")
        with col_m3:
            st.metric("Observations", f"{len(ridge_rec['actuals'])}")

        st.markdown("---")

        # Scatter plot: Actual vs Predicted
        st.markdown("### Prediction Accuracy")

        fig_scatter_rec = go.Figure()
        fig_scatter_rec.add_trace(
            go.Scatter(
                x=ridge_rec["actuals"],
                y=ridge_rec["predictions"],
                mode="markers",
                marker=dict(color="coral", size=8, opacity=0.7, line=dict(color="black", width=1)),
                name="Observations",
                hovertemplate="Actual: %{x:.0f}<br>Predicted: %{y:.0f}<extra></extra>",
            )
        )
        min_val_rec = min(ridge_rec["actuals"].min(), ridge_rec["predictions"].min())
        max_val_rec = max(ridge_rec["actuals"].max(), ridge_rec["predictions"].max())
        fig_scatter_rec.add_trace(
            go.Scatter(
                x=[min_val_rec, max_val_rec],
                y=[min_val_rec, max_val_rec],
                mode="lines",
                line=dict(color="#E74C3C", dash="dash", width=2),
                name="Perfect Fit",
            )
        )
        fig_scatter_rec.update_layout(
            title=f"Recovery Prediction (R² = {ridge_rec['r2']:.2f})",
            xaxis_title="Actual Recovery",
            yaxis_title="Predicted Recovery",
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_scatter_rec, use_container_width=True)

        st.markdown("---")

        # Timeline plot
        st.markdown("### Recovery Over Time")

        sorted_idx = np.argsort(ridge_rec["dates"])
        sorted_dates = ridge_rec["dates"][sorted_idx]
        sorted_actuals = ridge_rec["actuals"][sorted_idx]
        sorted_preds = ridge_rec["predictions"][sorted_idx]

        fig_timeline_rec = go.Figure()
        fig_timeline_rec.add_trace(
            go.Scatter(
                x=sorted_dates,
                y=sorted_actuals,
                mode="lines+markers",
                name="Actual",
                line=dict(color="#3498DB", width=2),
                marker=dict(size=5),
            )
        )
        fig_timeline_rec.add_trace(
            go.Scatter(
                x=sorted_dates,
                y=sorted_preds,
                mode="lines+markers",
                name="Predicted",
                line=dict(color="#E74C3C", width=2, dash="dash"),
                marker=dict(size=5),
            )
        )

        fig_timeline_rec.update_layout(
            title=f"Recovery Score: Actual vs Predicted (R² = {ridge_rec['r2']:.3f}, MAE = {ridge_rec['mae']:.2f})",
            xaxis_title="Date",
            yaxis_title="Recovery Score",
            height=500,
            margin=dict(l=0, r=0, t=50, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_timeline_rec, use_container_width=True)

        st.markdown("---")

        # Feature importance - horizontal bar chart
        st.markdown("### Feature Importance (Ridge Coefficients, Standardized)")

        coef_df_ridge = pd.DataFrame({
            "Feature": ridge_rec["feature_names"],
            "Coefficient": ridge_rec["coefficients"],
        }).sort_values("Coefficient", key=abs, ascending=True)

        colors_ridge = coef_df_ridge["Coefficient"].apply(
            lambda x: "#27AE60" if x > 0 else "#E74C3C"
        )

        fig_importance_rec = go.Figure()
        fig_importance_rec.add_trace(
            go.Bar(
                x=coef_df_ridge["Coefficient"],
                y=coef_df_ridge["Feature"],
                orientation="h",
                marker_color=colors_ridge,
                text=coef_df_ridge["Coefficient"].round(2),
                textposition="outside",
            )
        )

        fig_importance_rec.add_vline(x=0, line_dash="dash", line_color="#7F8C8D", opacity=0.5)

        fig_importance_rec.update_layout(
            title="Standardized Ridge Coefficients<br><sub>Green = positive effect | Red = negative effect</sub>",
            xaxis_title="Effect on Recovery Score",
            yaxis_title="",
            height=400,
            margin=dict(l=0, r=0, t=80, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_importance_rec, use_container_width=True)

with tab7:
    st.subheader("Ridge Regression: Predicting HRV")

    st.markdown("""
    This model predicts **HRV (Heart Rate Variability)** using Ridge regression with standardized features.
    The timeline below shows how well the model tracks actual HRV over time.
    """)

    df_mlr_hrv = prepare_hrv_mlr_data(
        cycles_filtered, recoveries_filtered, sleeps_filtered, workouts_filtered
    )

    ridge_hrv = fit_hrv_ridge_model(df_mlr_hrv)

    if ridge_hrv is None:
        st.warning("Not enough data for Ridge model. Need at least 10 complete observations.")
    else:
        # Model stats
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("R²", f"{ridge_hrv['r2']:.3f}")
        with col_m2:
            st.metric("MAE", f"{ridge_hrv['mae']:.2f}")
        with col_m3:
            st.metric("Observations", f"{len(ridge_hrv['actuals'])}")

        st.markdown("---")

        # Scatter plot: Actual vs Predicted
        st.markdown("### Prediction Accuracy")

        fig_scatter_hrv = go.Figure()
        fig_scatter_hrv.add_trace(
            go.Scatter(
                x=ridge_hrv["actuals"],
                y=ridge_hrv["predictions"],
                mode="markers",
                marker=dict(color="steelblue", size=8, opacity=0.7, line=dict(color="black", width=1)),
                name="Observations",
                hovertemplate="Actual: %{x:.1f}<br>Predicted: %{y:.1f}<extra></extra>",
            )
        )
        min_val_hrv = min(ridge_hrv["actuals"].min(), ridge_hrv["predictions"].min())
        max_val_hrv = max(ridge_hrv["actuals"].max(), ridge_hrv["predictions"].max())
        fig_scatter_hrv.add_trace(
            go.Scatter(
                x=[min_val_hrv, max_val_hrv],
                y=[min_val_hrv, max_val_hrv],
                mode="lines",
                line=dict(color="#E74C3C", dash="dash", width=2),
                name="Perfect Fit",
            )
        )
        fig_scatter_hrv.update_layout(
            title=f"HRV Prediction (R² = {ridge_hrv['r2']:.2f})",
            xaxis_title="Actual HRV (ms)",
            yaxis_title="Predicted HRV (ms)",
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_scatter_hrv, use_container_width=True)

        st.markdown("---")

        # Timeline plot
        st.markdown("### HRV Over Time")

        sorted_idx_hrv = np.argsort(ridge_hrv["dates"])
        sorted_dates_hrv = ridge_hrv["dates"][sorted_idx_hrv]
        sorted_actuals_hrv = ridge_hrv["actuals"][sorted_idx_hrv]
        sorted_preds_hrv = ridge_hrv["predictions"][sorted_idx_hrv]

        fig_timeline_hrv = go.Figure()
        fig_timeline_hrv.add_trace(
            go.Scatter(
                x=sorted_dates_hrv,
                y=sorted_actuals_hrv,
                mode="lines+markers",
                name="Actual",
                line=dict(color="#3498DB", width=2),
                marker=dict(size=5),
            )
        )
        fig_timeline_hrv.add_trace(
            go.Scatter(
                x=sorted_dates_hrv,
                y=sorted_preds_hrv,
                mode="lines+markers",
                name="Predicted",
                line=dict(color="#E74C3C", width=2, dash="dash"),
                marker=dict(size=5),
            )
        )

        fig_timeline_hrv.update_layout(
            title=f"HRV (ms): Actual vs Predicted (R² = {ridge_hrv['r2']:.3f}, MAE = {ridge_hrv['mae']:.2f})",
            xaxis_title="Date",
            yaxis_title="HRV (ms)",
            height=500,
            margin=dict(l=0, r=0, t=50, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_timeline_hrv, use_container_width=True)

        st.markdown("---")

        # Feature importance - horizontal bar chart
        st.markdown("### Feature Importance (Ridge Coefficients, Standardized)")

        coef_df_ridge_hrv = pd.DataFrame({
            "Feature": ridge_hrv["feature_names"],
            "Coefficient": ridge_hrv["coefficients"],
        }).sort_values("Coefficient", key=abs, ascending=True)

        colors_ridge_hrv = coef_df_ridge_hrv["Coefficient"].apply(
            lambda x: "#27AE60" if x > 0 else "#E74C3C"
        )

        fig_importance_hrv = go.Figure()
        fig_importance_hrv.add_trace(
            go.Bar(
                x=coef_df_ridge_hrv["Coefficient"],
                y=coef_df_ridge_hrv["Feature"],
                orientation="h",
                marker_color=colors_ridge_hrv,
                text=coef_df_ridge_hrv["Coefficient"].round(2),
                textposition="outside",
            )
        )

        fig_importance_hrv.add_vline(x=0, line_dash="dash", line_color="#7F8C8D", opacity=0.5)

        fig_importance_hrv.update_layout(
            title="Standardized Ridge Coefficients<br><sub>Green = positive effect | Red = negative effect</sub>",
            xaxis_title="Effect on HRV (ms)",
            yaxis_title="",
            height=450,
            margin=dict(l=0, r=0, t=80, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_importance_hrv, use_container_width=True)


st.markdown("---")
st.header("Data Tables")

table_select = st.selectbox(
    "Select data to view", ["Cycles", "Recoveries", "Sleeps", "Workouts"]
)

if table_select == "Cycles":
    st.dataframe(
        cycles_filtered.sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
elif table_select == "Recoveries":
    st.dataframe(
        recoveries_filtered.sort_values("updated_at", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
elif table_select == "Sleeps":
    st.dataframe(
        sleeps_filtered.sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
elif table_select == "Workouts":
    st.dataframe(
        workouts_filtered.sort_values("date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
