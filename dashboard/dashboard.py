import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import statsmodels.api as sm
from scipy import stats
import os

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
    st.plotly_chart(fig, width="stretch")

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
    st.plotly_chart(fig_stages, width="stretch")

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
    st.plotly_chart(fig_perf, width="stretch")

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
    st.plotly_chart(fig, width="stretch")

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
            st.plotly_chart(fig, width="stretch")

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
            st.plotly_chart(fig, width="stretch")

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
        st.dataframe(workout_display, width="stretch", hide_index=True)
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
    st.plotly_chart(fig_corr, width="stretch")

    st.markdown("### Key Relationships")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Sleep vs Next Day Recovery")
        fig_sleep_rec = px.scatter(
            df_insights,
            x="sleep_hrs",
            y="recovery_score",
            trendline="ols",
            title="Sleep Hours vs Recovery Score",
            labels={"sleep_hrs": "Sleep (hours)", "recovery_score": "Recovery (%)"},
        )
        fig_sleep_rec.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_sleep_rec, width="stretch")

        if df_insights["sleep_hrs"].notna().sum() > 2:
            corr_val = df_insights["sleep_hrs"].corr(df_insights["recovery_score"])
            st.info(f"Correlation: **{corr_val:.2f}**")

    with col2:
        st.markdown("#### HRV vs Recovery")
        fig_hrv_rec = px.scatter(
            df_insights,
            x="hrv_rmssd_milli",
            y="recovery_score",
            trendline="ols",
            title="HRV vs Recovery Score",
            labels={"hrv_rmssd_milli": "HRV (ms)", "recovery_score": "Recovery (%)"},
            color_discrete_sequence=["#9B59B6"],
        )
        fig_hrv_rec.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_hrv_rec, width="stretch")

        if df_insights["hrv_rmssd_milli"].notna().sum() > 2:
            corr_val = df_insights["hrv_rmssd_milli"].corr(
                df_insights["recovery_score"]
            )
            st.info(f"Correlation: **{corr_val:.2f}**")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Strain vs RHR")
        fig_strain_rhr = px.scatter(
            df_insights,
            x="strain",
            y="resting_heart_rate",
            trendline="ols",
            title="Daily Strain vs Resting HR",
            labels={"strain": "Strain", "resting_heart_rate": "RHR (bpm)"},
            color_discrete_sequence=["#E74C3C"],
        )
        fig_strain_rhr.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_strain_rhr, width="stretch")

        if df_insights["strain"].notna().sum() > 2:
            corr_val = df_insights["strain"].corr(df_insights["resting_heart_rate"])
            st.info(f"Correlation: **{corr_val:.2f}**")

    with col4:
        st.markdown("#### Deep Sleep vs Recovery")
        fig_deep_rec = px.scatter(
            df_insights,
            x="deep_sleep_hrs",
            y="recovery_score",
            trendline="ols",
            title="Deep Sleep vs Recovery",
            labels={
                "deep_sleep_hrs": "Deep Sleep (hrs)",
                "recovery_score": "Recovery (%)",
            },
            color_discrete_sequence=["#2E86AB"],
        )
        fig_deep_rec.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_deep_rec, width="stretch")

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
        st.dataframe(best_days, hide_index=True, width="stretch")

    with col6:
        st.markdown("#### Worst Recovery Days")
        worst_days = df_insights.nsmallest(5, "recovery_score")[
            ["date", "recovery_score", "sleep_hrs", "hrv_rmssd_milli"]
        ]
        worst_days.columns = ["Date", "Recovery", "Sleep Hrs", "HRV"]
        st.dataframe(worst_days, hide_index=True, width="stretch")

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
    st.subheader("Multiple Linear Regression: Predicting Recovery")

    st.markdown("""
    This model predicts **Recovery Score** using multiple physiological and behavioral features.
    The coefficients show the **unique contribution** of each predictor when controlling for all others.
    """)

    df_mlr = (
        cycles_filtered[["date", "strain", "id", "max_heart_rate"]]
        .merge(
            recoveries_filtered[
                ["cycle_id", "recovery_score", "hrv_rmssd_milli", "resting_heart_rate"]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
        .merge(
            sleeps_filtered[
                [
                    "cycle_id",
                    "total_slow_wave_sleep_time_milli",
                    "total_rem_sleep_time_milli",
                    "total_light_sleep_time_milli",
                    "sleep_efficiency_percentage",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
    )

    if not workouts_filtered.empty:
        workout_dates = set(workouts_filtered["date"])
        df_mlr["had_workout"] = df_mlr["date"].isin(workout_dates).astype(int)
    else:
        df_mlr["had_workout"] = 0

    df_mlr["deep_sleep_hrs"] = df_mlr["total_slow_wave_sleep_time_milli"] / 3600000
    df_mlr["rem_sleep_hrs"] = df_mlr["total_rem_sleep_time_milli"] / 3600000
    df_mlr["total_sleep_hrs"] = (
        df_mlr["total_slow_wave_sleep_time_milli"]
        + df_mlr["total_rem_sleep_time_milli"]
        + df_mlr["total_light_sleep_time_milli"]
    ) / 3600000

    feature_cols = [
        "deep_sleep_hrs",
        "rem_sleep_hrs",
        "hrv_rmssd_milli",
        "max_heart_rate",
        "strain",
        "had_workout",
    ]
    target_col = "recovery_score"

    df_model = df_mlr[feature_cols + [target_col, "date"]].dropna()

    if len(df_model) < 10:
        st.warning(
            f"Not enough data for MLR model. Need at least 10 complete observations, have {len(df_model)}."
        )
    else:
        st.markdown(f"**Sample Size:** {len(df_model)} observations")

        X = df_model[feature_cols]
        y = df_model[target_col]

        X_std = (X - X.mean()) / X.std()
        X_std = sm.add_constant(X_std)

        model = sm.OLS(y, X_std).fit()

        col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
        with col_metrics1:
            st.metric("R²", f"{model.rsquared:.3f}")
        with col_metrics2:
            st.metric("Adj. R²", f"{model.rsquared_adj:.3f}")
        with col_metrics3:
            st.metric("F-statistic", f"{model.fvalue:.2f}")
        with col_metrics4:
            st.metric("Prob (F-stat)", f"{model.f_pvalue:.4f}")

        st.markdown("---")

        st.markdown("### Model Coefficients (Standardized)")
        st.markdown("""
        Standardized coefficients allow comparison of relative importance across predictors.
        A positive coefficient means higher values of that predictor are associated with **higher recovery**,
        controlling for all other variables.
        """)

        coef_df = pd.DataFrame(
            {
                "Feature": [
                    "Intercept",
                    "Deep Sleep (hrs)",
                    "REM Sleep (hrs)",
                    "HRV (ms)",
                    "Max HR (bpm)",
                    "Strain",
                    "Had Workout",
                ],
                "Coefficient": model.params.values,
                "Std Error": model.bse.values,
                "t-value": model.tvalues.values,
                "P-value": model.pvalues.values,
            }
        )

        coef_df["Significant"] = coef_df["P-value"] < 0.05
        coef_df["CI Lower"] = model.conf_int()[0].values
        coef_df["CI Upper"] = model.conf_int()[1].values

        coef_plot_df = coef_df[coef_df["Feature"] != "Intercept"].copy()

        fig_coef = go.Figure()

        colors = coef_plot_df.apply(
            lambda row: "#27AE60"
            if row["Coefficient"] > 0 and row["Significant"]
            else "#E74C3C"
            if row["Coefficient"] < 0 and row["Significant"]
            else "#95A5A6",
            axis=1,
        )

        fig_coef.add_trace(
            go.Bar(
                x=coef_plot_df["Feature"],
                y=coef_plot_df["Coefficient"],
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=coef_plot_df["CI Upper"] - coef_plot_df["Coefficient"],
                    arrayminus=coef_plot_df["Coefficient"] - coef_plot_df["CI Lower"],
                    color="#7F8C8D",
                ),
                marker_color=colors,
                text=coef_plot_df["Coefficient"].round(2),
                textposition="outside",
            )
        )

        fig_coef.add_hline(y=0, line_dash="dash", line_color="#7F8C8D", opacity=0.5)

        fig_coef.update_layout(
            title="Standardized Coefficients with 95% CI<br><sub>Green = Significant positive effect | Red = Significant negative effect | Gray = Not significant</sub>",
            xaxis_title="Predictor",
            yaxis_title="Effect on Recovery Score",
            height=450,
            margin=dict(l=0, r=0, t=80, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_coef, width="stretch")

        st.markdown("---")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Actual vs Predicted")

            y_pred = model.predict(X_std)

            fig_pred = go.Figure()

            fig_pred.add_trace(
                go.Scatter(
                    x=y,
                    y=y_pred,
                    mode="markers",
                    marker=dict(color="#3498DB", size=8, opacity=0.7),
                    name="Observations",
                    hovertemplate="Actual: %{x:.0f}<br>Predicted: %{y:.0f}<extra></extra>",
                )
            )

            min_val = min(y.min(), y_pred.min())
            max_val = max(y.max(), y_pred.max())
            fig_pred.add_trace(
                go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode="lines",
                    line=dict(color="#E74C3C", dash="dash"),
                    name="Perfect Fit",
                )
            )

            fig_pred.update_layout(
                title=f"Model Fit (R² = {model.rsquared:.3f})",
                xaxis_title="Actual Recovery Score",
                yaxis_title="Predicted Recovery Score",
                height=400,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
            )
            st.plotly_chart(fig_pred, width="stretch")

        with col_right:
            st.markdown("### Residuals Distribution")

            residuals = y - y_pred

            fig_resid = go.Figure()

            fig_resid.add_trace(
                go.Histogram(
                    x=residuals,
                    nbinsx=20,
                    marker_color="#9B59B6",
                    opacity=0.7,
                    name="Residuals",
                )
            )

            fig_resid.add_vline(x=0, line_dash="dash", line_color="#E74C3C")

            fig_resid.update_layout(
                title=f"Residuals (Mean = {residuals.mean():.2f}, SD = {residuals.std():.2f})",
                xaxis_title="Residual (Actual - Predicted)",
                yaxis_title="Frequency",
                height=400,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False,
            )
            st.plotly_chart(fig_resid, width="stretch")

        st.markdown("---")

        st.markdown("### Detailed Coefficient Table")

        display_coef = coef_df.copy()
        display_coef["P-value"] = display_coef["P-value"].apply(
            lambda x: f"{x:.4f}" + (" *" if x < 0.05 else "")
        )
        display_coef["Coefficient"] = display_coef["Coefficient"].round(3)
        display_coef["Std Error"] = display_coef["Std Error"].round(3)
        display_coef["t-value"] = display_coef["t-value"].round(2)

        st.dataframe(
            display_coef[["Feature", "Coefficient", "Std Error", "t-value", "P-value"]],
            width="stretch",
            hide_index=True,
        )

        st.markdown(
            "<sub>* p < 0.05 (statistically significant)</sub>", unsafe_allow_html=True
        )

        st.markdown("---")

        st.markdown("### 💡 Key Insights")

        insights = []
        sig_coefs = coef_df[
            (coef_df["Significant"]) & (coef_df["Feature"] != "Intercept")
        ]

        for _, row in sig_coefs.iterrows():
            direction = "increases" if row["Coefficient"] > 0 else "decreases"
            effect_size = abs(row["Coefficient"])
            if effect_size > 5:
                magnitude = "strongly"
            elif effect_size > 2:
                magnitude = "moderately"
            else:
                magnitude = "slightly"

            insights.append(
                f"- **{row['Feature']}** {magnitude} {direction} recovery (β = {row['Coefficient']:.2f}, p = {row['P-value']:.4f})"
            )

        if insights:
            for insight in insights:
                st.markdown(insight)
        else:
            st.info("No predictors reached statistical significance at p < 0.05 level.")

        st.markdown("---")

        st.markdown("### Partial Correlations (Controlling for Other Features)")

        st.markdown("""
        Partial correlations show the unique relationship between each predictor and recovery, 
        **after removing the effects of all other predictors**. This is different from simple correlations 
        which don't account for confounding variables.
        """)

        df_resid = model.df_resid
        partial_corrs = []
        for i, feat in enumerate(feature_cols):
            t_val = model.tvalues.iloc[i + 1]
            partial_r = t_val / np.sqrt(t_val**2 + df_resid)
            partial_corrs.append(partial_r)

        partial_corr_df = pd.DataFrame(
            {
                "Feature": [
                    "Deep Sleep (hrs)",
                    "REM Sleep (hrs)",
                    "HRV (ms)",
                    "Max HR (bpm)",
                    "Strain",
                    "Had Workout",
                ],
                "Partial Correlation": partial_corrs,
            }
        )

        colors_partial = partial_corr_df["Partial Correlation"].apply(
            lambda x: "#27AE60" if x > 0 else "#E74C3C"
        )

        fig_partial = go.Figure()
        fig_partial.add_trace(
            go.Bar(
                x=partial_corr_df["Feature"],
                y=partial_corr_df["Partial Correlation"],
                marker_color=colors_partial,
                text=partial_corr_df["Partial Correlation"].round(2),
                textposition="outside",
            )
        )

        fig_partial.add_hline(y=0, line_dash="dash", line_color="#7F8C8D", opacity=0.5)

        fig_partial.update_layout(
            title="Partial Correlations: Unique Contribution of Each Predictor",
            xaxis_title="Predictor",
            yaxis_title="Partial Correlation",
            height=400,
            margin=dict(l=0, r=0, t=50, b=0),
            showlegend=False,
            yaxis_range=[-1, 1],
        )
        st.plotly_chart(fig_partial, width="stretch")

        col_partial1, col_partial2 = st.columns(2)
        with col_partial1:
            st.markdown("**Interpretation:**")
            st.markdown("""
            - **Positive values**: Higher predictor → Higher recovery (controlling for others)
            - **Negative values**: Higher predictor → Lower recovery (controlling for others)
            - **Magnitude**: Strength of unique relationship
            """)
        with col_partial2:
            st.markdown("**Top Contributors:**")
            top_predictors = partial_corr_df.reindex(
                partial_corr_df["Partial Correlation"]
                .abs()
                .sort_values(ascending=False)
                .index
            ).head(3)
            for _, row in top_predictors.iterrows():
                st.markdown(f"- **{row['Feature']}**: {row['Partial Correlation']:.2f}")

with tab7:
    st.subheader("Multiple Linear Regression: Predicting HRV")

    st.markdown("""
    This model predicts **HRV (Heart Rate Variability)** using multiple physiological and behavioral features.
    HRV is a key indicator of autonomic nervous system function and recovery capacity.
    """)

    df_mlr_hrv = (
        cycles_filtered[
            ["date", "strain", "id", "max_heart_rate", "average_heart_rate"]
        ]
        .merge(
            recoveries_filtered[
                ["cycle_id", "recovery_score", "hrv_rmssd_milli", "resting_heart_rate"]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
        .merge(
            sleeps_filtered[
                [
                    "cycle_id",
                    "total_slow_wave_sleep_time_milli",
                    "total_rem_sleep_time_milli",
                    "total_light_sleep_time_milli",
                    "sleep_efficiency_percentage",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
    )

    if not workouts_filtered.empty:
        workout_dates = set(workouts_filtered["date"])
        df_mlr_hrv["had_workout"] = df_mlr_hrv["date"].isin(workout_dates).astype(int)
    else:
        df_mlr_hrv["had_workout"] = 0

    df_mlr_hrv["deep_sleep_hrs"] = (
        df_mlr_hrv["total_slow_wave_sleep_time_milli"] / 3600000
    )
    df_mlr_hrv["rem_sleep_hrs"] = df_mlr_hrv["total_rem_sleep_time_milli"] / 3600000
    df_mlr_hrv["total_sleep_hrs"] = (
        df_mlr_hrv["total_slow_wave_sleep_time_milli"]
        + df_mlr_hrv["total_rem_sleep_time_milli"]
        + df_mlr_hrv["total_light_sleep_time_milli"]
    ) / 3600000

    feature_cols_hrv = [
        "deep_sleep_hrs",
        "rem_sleep_hrs",
        "recovery_score",
        "max_heart_rate",
        "strain",
        "had_workout",
    ]
    target_col_hrv = "hrv_rmssd_milli"

    df_model_hrv = df_mlr_hrv[feature_cols_hrv + [target_col_hrv, "date"]].dropna()

    if len(df_model_hrv) < 10:
        st.warning(
            f"Not enough data for MLR model. Need at least 10 complete observations, have {len(df_model_hrv)}."
        )
    else:
        st.markdown(f"**Sample Size:** {len(df_model_hrv)} observations")

        X_hrv = df_model_hrv[feature_cols_hrv]
        y_hrv = df_model_hrv[target_col_hrv]

        X_std_hrv = (X_hrv - X_hrv.mean()) / X_hrv.std()
        X_std_hrv = sm.add_constant(X_std_hrv)

        model_hrv = sm.OLS(y_hrv, X_std_hrv).fit()

        col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
        with col_metrics1:
            st.metric("R²", f"{model_hrv.rsquared:.3f}")
        with col_metrics2:
            st.metric("Adj. R²", f"{model_hrv.rsquared_adj:.3f}")
        with col_metrics3:
            st.metric("F-statistic", f"{model_hrv.fvalue:.2f}")
        with col_metrics4:
            st.metric("Prob (F-stat)", f"{model_hrv.f_pvalue:.4f}")

        st.markdown("---")

        st.markdown("### Model Coefficients (Standardized)")
        st.markdown("""
        Standardized coefficients allow comparison of relative importance across predictors.
        A positive coefficient means higher values of that predictor are associated with **higher HRV**,
        controlling for all other variables.
        """)

        coef_df_hrv = pd.DataFrame(
            {
                "Feature": [
                    "Intercept",
                    "Deep Sleep (hrs)",
                    "REM Sleep (hrs)",
                    "Recovery Score",
                    "Max HR (bpm)",
                    "Strain",
                    "Had Workout",
                ],
                "Coefficient": model_hrv.params.values,
                "Std Error": model_hrv.bse.values,
                "t-value": model_hrv.tvalues.values,
                "P-value": model_hrv.pvalues.values,
            }
        )

        coef_df_hrv["Significant"] = coef_df_hrv["P-value"] < 0.05
        coef_df_hrv["CI Lower"] = model_hrv.conf_int()[0].values
        coef_df_hrv["CI Upper"] = model_hrv.conf_int()[1].values

        coef_plot_df_hrv = coef_df_hrv[coef_df_hrv["Feature"] != "Intercept"].copy()

        fig_coef_hrv = go.Figure()

        colors_hrv = coef_plot_df_hrv.apply(
            lambda row: "#27AE60"
            if row["Coefficient"] > 0 and row["Significant"]
            else "#E74C3C"
            if row["Coefficient"] < 0 and row["Significant"]
            else "#95A5A6",
            axis=1,
        )

        fig_coef_hrv.add_trace(
            go.Bar(
                x=coef_plot_df_hrv["Feature"],
                y=coef_plot_df_hrv["Coefficient"],
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=coef_plot_df_hrv["CI Upper"]
                    - coef_plot_df_hrv["Coefficient"],
                    arrayminus=coef_plot_df_hrv["Coefficient"]
                    - coef_plot_df_hrv["CI Lower"],
                    color="#7F8C8D",
                ),
                marker_color=colors_hrv,
                text=coef_plot_df_hrv["Coefficient"].round(2),
                textposition="outside",
            )
        )

        fig_coef_hrv.add_hline(y=0, line_dash="dash", line_color="#7F8C8D", opacity=0.5)

        fig_coef_hrv.update_layout(
            title="Standardized Coefficients with 95% CI<br><sub>Green = Significant positive effect | Red = Significant negative effect | Gray = Not significant</sub>",
            xaxis_title="Predictor",
            yaxis_title="Effect on HRV (ms)",
            height=450,
            margin=dict(l=0, r=0, t=80, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_coef_hrv, width="stretch")

        st.markdown("---")

        col_left_hrv, col_right_hrv = st.columns(2)

        with col_left_hrv:
            st.markdown("### Actual vs Predicted")

            y_pred_hrv = model_hrv.predict(X_std_hrv)

            fig_pred_hrv = go.Figure()

            fig_pred_hrv.add_trace(
                go.Scatter(
                    x=y_hrv,
                    y=y_pred_hrv,
                    mode="markers",
                    marker=dict(color="#9B59B6", size=8, opacity=0.7),
                    name="Observations",
                    hovertemplate="Actual: %{x:.1f}<br>Predicted: %{y:.1f}<extra></extra>",
                )
            )

            min_val_hrv = min(y_hrv.min(), y_pred_hrv.min())
            max_val_hrv = max(y_hrv.max(), y_pred_hrv.max())
            fig_pred_hrv.add_trace(
                go.Scatter(
                    x=[min_val_hrv, max_val_hrv],
                    y=[min_val_hrv, max_val_hrv],
                    mode="lines",
                    line=dict(color="#E74C3C", dash="dash"),
                    name="Perfect Fit",
                )
            )

            fig_pred_hrv.update_layout(
                title=f"Model Fit (R² = {model_hrv.rsquared:.3f})",
                xaxis_title="Actual HRV (ms)",
                yaxis_title="Predicted HRV (ms)",
                height=400,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
            )
            st.plotly_chart(fig_pred_hrv, width="stretch")

        with col_right_hrv:
            st.markdown("### Residuals Distribution")

            residuals_hrv = y_hrv - y_pred_hrv

            fig_resid_hrv = go.Figure()

            fig_resid_hrv.add_trace(
                go.Histogram(
                    x=residuals_hrv,
                    nbinsx=20,
                    marker_color="#3498DB",
                    opacity=0.7,
                    name="Residuals",
                )
            )

            fig_resid_hrv.add_vline(x=0, line_dash="dash", line_color="#E74C3C")

            fig_resid_hrv.update_layout(
                title=f"Residuals (Mean = {residuals_hrv.mean():.2f}, SD = {residuals_hrv.std():.2f})",
                xaxis_title="Residual (Actual - Predicted)",
                yaxis_title="Frequency",
                height=400,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False,
            )
            st.plotly_chart(fig_resid_hrv, width="stretch")

        st.markdown("---")

        st.markdown("### Detailed Coefficient Table")

        display_coef_hrv = coef_df_hrv.copy()
        display_coef_hrv["P-value"] = display_coef_hrv["P-value"].apply(
            lambda x: f"{x:.4f}" + (" *" if x < 0.05 else "")
        )
        display_coef_hrv["Coefficient"] = display_coef_hrv["Coefficient"].round(3)
        display_coef_hrv["Std Error"] = display_coef_hrv["Std Error"].round(3)
        display_coef_hrv["t-value"] = display_coef_hrv["t-value"].round(2)

        st.dataframe(
            display_coef_hrv[
                ["Feature", "Coefficient", "Std Error", "t-value", "P-value"]
            ],
            width="stretch",
            hide_index=True,
        )

        st.markdown(
            "<sub>* p < 0.05 (statistically significant)</sub>", unsafe_allow_html=True
        )

        st.markdown("---")

        st.markdown("### 💡 Key Insights")

        insights_hrv = []
        sig_coefs_hrv = coef_df_hrv[
            (coef_df_hrv["Significant"]) & (coef_df_hrv["Feature"] != "Intercept")
        ]

        for _, row in sig_coefs_hrv.iterrows():
            direction = "increases" if row["Coefficient"] > 0 else "decreases"
            effect_size = abs(row["Coefficient"])
            if effect_size > 3:
                magnitude = "strongly"
            elif effect_size > 1:
                magnitude = "moderately"
            else:
                magnitude = "slightly"

            insights_hrv.append(
                f"- **{row['Feature']}** {magnitude} {direction} HRV (β = {row['Coefficient']:.2f}, p = {row['P-value']:.4f})"
            )

        if insights_hrv:
            for insight in insights_hrv:
                st.markdown(insight)
        else:
            st.info("No predictors reached statistical significance at p < 0.05 level.")

        st.markdown("---")

        st.markdown("### Partial Correlations (Controlling for Other Features)")

        st.markdown("""
        Partial correlations show the unique relationship between each predictor and HRV, 
        **after removing the effects of all other predictors**. This is different from simple correlations 
        which don't account for confounding variables.
        """)

        df_resid_hrv = model_hrv.df_resid
        partial_corrs_hrv = []
        for i, feat in enumerate(feature_cols_hrv):
            t_val = model_hrv.tvalues.iloc[i + 1]
            partial_r = t_val / np.sqrt(t_val**2 + df_resid_hrv)
            partial_corrs_hrv.append(partial_r)

        partial_corr_df_hrv = pd.DataFrame(
            {
                "Feature": [
                    "Deep Sleep (hrs)",
                    "REM Sleep (hrs)",
                    "Recovery Score",
                    "Max HR (bpm)",
                    "Strain",
                    "Had Workout",
                ],
                "Partial Correlation": partial_corrs_hrv,
            }
        )

        colors_partial_hrv = partial_corr_df_hrv["Partial Correlation"].apply(
            lambda x: "#27AE60" if x > 0 else "#E74C3C"
        )

        fig_partial_hrv = go.Figure()
        fig_partial_hrv.add_trace(
            go.Bar(
                x=partial_corr_df_hrv["Feature"],
                y=partial_corr_df_hrv["Partial Correlation"],
                marker_color=colors_partial_hrv,
                text=partial_corr_df_hrv["Partial Correlation"].round(2),
                textposition="outside",
            )
        )

        fig_partial_hrv.add_hline(
            y=0, line_dash="dash", line_color="#7F8C8D", opacity=0.5
        )

        fig_partial_hrv.update_layout(
            title="Partial Correlations: Unique Contribution of Each Predictor",
            xaxis_title="Predictor",
            yaxis_title="Partial Correlation",
            height=400,
            margin=dict(l=0, r=0, t=50, b=0),
            showlegend=False,
            yaxis_range=[-1, 1],
        )
        st.plotly_chart(fig_partial_hrv, width="stretch")

        col_partial1_hrv, col_partial2_hrv = st.columns(2)
        with col_partial1_hrv:
            st.markdown("**Interpretation:**")
            st.markdown("""
            - **Positive values**: Higher predictor → Higher HRV (controlling for others)
            - **Negative values**: Higher predictor → Lower HRV (controlling for others)
            - **Magnitude**: Strength of unique relationship
            """)
        with col_partial2_hrv:
            st.markdown("**Top Contributors:**")
            top_predictors_hrv = partial_corr_df_hrv.reindex(
                partial_corr_df_hrv["Partial Correlation"]
                .abs()
                .sort_values(ascending=False)
                .index
            ).head(3)
            for _, row in top_predictors_hrv.iterrows():
                st.markdown(f"- **{row['Feature']}**: {row['Partial Correlation']:.2f}")


st.markdown("---")
st.header("Data Tables")

table_select = st.selectbox(
    "Select data to view", ["Cycles", "Recoveries", "Sleeps", "Workouts"]
)

if table_select == "Cycles":
    st.dataframe(
        cycles_filtered.sort_values("date", ascending=False),
        width="stretch",
        hide_index=True,
    )
elif table_select == "Recoveries":
    st.dataframe(
        recoveries_filtered.sort_values("updated_at", ascending=False),
        width="stretch",
        hide_index=True,
    )
elif table_select == "Sleeps":
    st.dataframe(
        sleeps_filtered.sort_values("date", ascending=False),
        width="stretch",
        hide_index=True,
    )
elif table_select == "Workouts":
    st.dataframe(
        workouts_filtered.sort_values("date", ascending=False),
        width="stretch",
        hide_index=True,
    )
