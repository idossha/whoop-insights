import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error


def prepare_recovery_mlr_data(cycles_df, recoveries_df, sleeps_df, workouts_df):
    df_mlr = (
        cycles_df[["date", "strain", "id", "max_heart_rate"]]
        .merge(
            recoveries_df[
                ["cycle_id", "recovery_score", "hrv_rmssd_milli", "resting_heart_rate"]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
        .merge(
            sleeps_df[
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

    if not workouts_df.empty:
        workout_dates = set(workouts_df["date"])
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

    return df_mlr


def prepare_hrv_mlr_data(cycles_df, recoveries_df, sleeps_df, workouts_df):
    df_mlr_hrv = (
        cycles_df[
            [
                "date",
                "strain",
                "id",
                "max_heart_rate",
                "average_heart_rate",
                "kilojoule",
            ]
        ]
        .rename(columns={"strain": "day_strain"})
        .merge(
            recoveries_df[
                [
                    "cycle_id",
                    "hrv_rmssd_milli",
                    "resting_heart_rate",
                    "spo2_percentage",
                    "skin_temp_celsius",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
        .merge(
            sleeps_df[
                [
                    "cycle_id",
                    "total_slow_wave_sleep_time_milli",
                    "total_rem_sleep_time_milli",
                    "total_light_sleep_time_milli",
                    "sleep_efficiency_percentage",
                    "respiratory_rate",
                    "sleep_consistency_percentage",
                    "disturbance_count",
                ]
            ],
            left_on="id",
            right_on="cycle_id",
            how="inner",
        )
    )

    if not workouts_df.empty:
        workout_agg = (
            workouts_df.groupby("date")
            .agg(
                workout_strain=("strain", "sum"),
                workout_kilojoule=("kilojoule", "sum"),
                workout_count=("id", "count"),
            )
            .reset_index()
        )
        df_mlr_hrv = df_mlr_hrv.merge(workout_agg, on="date", how="left")
        df_mlr_hrv["workout_strain"] = df_mlr_hrv["workout_strain"].fillna(0)
        df_mlr_hrv["workout_kilojoule"] = df_mlr_hrv["workout_kilojoule"].fillna(0)
        df_mlr_hrv["workout_count"] = df_mlr_hrv["workout_count"].fillna(0).astype(int)
    else:
        df_mlr_hrv["workout_strain"] = 0
        df_mlr_hrv["workout_kilojoule"] = 0
        df_mlr_hrv["workout_count"] = 0

    df_mlr_hrv["deep_sleep_hrs"] = (
        df_mlr_hrv["total_slow_wave_sleep_time_milli"] / 3600000
    )
    df_mlr_hrv["rem_sleep_hrs"] = df_mlr_hrv["total_rem_sleep_time_milli"] / 3600000
    df_mlr_hrv["total_sleep_hrs"] = (
        df_mlr_hrv["total_slow_wave_sleep_time_milli"]
        + df_mlr_hrv["total_rem_sleep_time_milli"]
        + df_mlr_hrv["total_light_sleep_time_milli"]
    ) / 3600000

    return df_mlr_hrv


def fit_recovery_ridge_model(df_mlr, alpha=1.0):
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
        return None

    X = df_model[feature_cols].values
    y = df_model[target_col].values
    dates = df_model["date"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = Ridge(alpha=alpha)
    model.fit(X_scaled, y)

    predictions = model.predict(X_scaled)

    feature_labels = [
        "Deep Sleep (hrs)",
        "REM Sleep (hrs)",
        "HRV (ms)",
        "Max HR (bpm)",
        "Strain",
        "Had Workout",
    ]

    return {
        "model": model,
        "scaler": scaler,
        "predictions": predictions,
        "dates": dates,
        "actuals": y,
        "r2": r2_score(y, predictions),
        "mae": mean_absolute_error(y, predictions),
        "feature_names": feature_labels,
        "coefficients": model.coef_,
    }


def fit_hrv_ridge_model(df_mlr_hrv, alpha=1.0):
    core_features = [
        "deep_sleep_hrs",
        "rem_sleep_hrs",
        "total_sleep_hrs",
        "sleep_efficiency_percentage",
        "resting_heart_rate",
        "respiratory_rate",
        "workout_strain",
        "day_strain",
    ]

    optional_features = ["spo2_percentage", "skin_temp_celsius", "disturbance_count"]

    available_optional = []
    for feat in optional_features:
        if feat in df_mlr_hrv.columns:
            non_null_count = df_mlr_hrv[feat].notna().sum()
            if non_null_count >= 10:
                available_optional.append(feat)

    feature_cols = core_features + available_optional
    target_col = "hrv_rmssd_milli"

    df_model = df_mlr_hrv[feature_cols + [target_col, "date"]].dropna()

    if len(df_model) < 10:
        return None

    X = df_model[feature_cols].values
    y = df_model[target_col].values
    dates = df_model["date"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = Ridge(alpha=alpha)
    model.fit(X_scaled, y)

    predictions = model.predict(X_scaled)

    feature_labels_map = {
        "deep_sleep_hrs": "Deep Sleep (hrs)",
        "rem_sleep_hrs": "REM Sleep (hrs)",
        "total_sleep_hrs": "Total Sleep (hrs)",
        "sleep_efficiency_percentage": "Sleep Efficiency (%)",
        "resting_heart_rate": "Resting HR (bpm)",
        "respiratory_rate": "Respiratory Rate",
        "workout_strain": "Workout Strain",
        "day_strain": "Day Strain",
        "spo2_percentage": "SpO2 (%)",
        "skin_temp_celsius": "Skin Temp (C)",
        "disturbance_count": "Disturbances",
    }

    feature_labels = [feature_labels_map[f] for f in feature_cols]

    return {
        "model": model,
        "scaler": scaler,
        "predictions": predictions,
        "dates": dates,
        "actuals": y,
        "r2": r2_score(y, predictions),
        "mae": mean_absolute_error(y, predictions),
        "feature_names": feature_labels,
        "coefficients": model.coef_,
    }
