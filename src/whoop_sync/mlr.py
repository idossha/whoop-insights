import pandas as pd
import numpy as np
import statsmodels.api as sm


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


def fit_recovery_mlr_model(df_mlr):
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
        return None, df_model

    X = df_model[feature_cols]
    y = df_model[target_col]

    X_std = (X - X.mean()) / X.std()
    X_std = sm.add_constant(X_std)

    model = sm.OLS(y, X_std).fit()

    return model, df_model


def get_recovery_model_results(model, df_model):
    feature_cols = [
        "deep_sleep_hrs",
        "rem_sleep_hrs",
        "hrv_rmssd_milli",
        "max_heart_rate",
        "strain",
        "had_workout",
    ]
    target_col = "recovery_score"

    X = df_model[feature_cols]
    y = df_model[target_col]

    X_std = (X - X.mean()) / X.std()
    X_std = sm.add_constant(X_std)

    y_pred = model.predict(X_std)
    residuals = y - y_pred

    feature_labels = [
        "Intercept",
        "Deep Sleep (hrs)",
        "REM Sleep (hrs)",
        "HRV (ms)",
        "Max HR (bpm)",
        "Strain",
        "Had Workout",
    ]

    coef_df = pd.DataFrame(
        {
            "Feature": feature_labels,
            "Coefficient": model.params.values,
            "Std Error": model.bse.values,
            "t-value": model.tvalues.values,
            "P-value": model.pvalues.values,
        }
    )

    coef_df["Significant"] = coef_df["P-value"] < 0.05
    coef_df["CI Lower"] = model.conf_int()[0].values
    coef_df["CI Upper"] = model.conf_int()[1].values

    df_resid = model.df_resid
    partial_corrs = []
    for i, feat in enumerate(feature_cols):
        t_val = model.tvalues.iloc[i + 1]
        partial_r = t_val / np.sqrt(t_val**2 + df_resid)
        partial_corrs.append(partial_r)

    partial_corr_df = pd.DataFrame(
        {
            "Feature": feature_labels[1:],
            "Partial Correlation": partial_corrs,
        }
    )

    return {
        "model": model,
        "y": y,
        "y_pred": y_pred,
        "residuals": residuals,
        "coef_df": coef_df,
        "partial_corr_df": partial_corr_df,
        "n_observations": len(df_model),
    }


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


def fit_hrv_mlr_model(df_mlr_hrv):
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

    feature_cols_hrv = core_features + available_optional
    target_col_hrv = "hrv_rmssd_milli"

    df_model_hrv = df_mlr_hrv[feature_cols_hrv + [target_col_hrv, "date"]].dropna()

    if len(df_model_hrv) < 10:
        return None, df_model_hrv, available_optional

    X_hrv = df_model_hrv[feature_cols_hrv]
    y_hrv = df_model_hrv[target_col_hrv]

    X_std_hrv = (X_hrv - X_hrv.mean()) / X_hrv.std()
    X_std_hrv = sm.add_constant(X_std_hrv)

    model_hrv = sm.OLS(y_hrv, X_std_hrv).fit()

    return model_hrv, df_model_hrv, available_optional


def get_hrv_model_results(model, df_model_hrv, available_optional):
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

    feature_cols_hrv = core_features + available_optional
    target_col_hrv = "hrv_rmssd_milli"

    feature_labels = {
        "deep_sleep_hrs": "Deep Sleep (hrs)",
        "rem_sleep_hrs": "REM Sleep (hrs)",
        "total_sleep_hrs": "Total Sleep (hrs)",
        "sleep_efficiency_percentage": "Sleep Efficiency (%)",
        "resting_heart_rate": "Resting HR (bpm)",
        "respiratory_rate": "Respiratory Rate",
        "workout_strain": "Workout Strain",
        "day_strain": "Day Strain",
        "spo2_percentage": "SpO2 (%)",
        "skin_temp_celsius": "Skin Temp (°C)",
        "disturbance_count": "Disturbances",
    }

    X_hrv = df_model_hrv[feature_cols_hrv]
    y_hrv = df_model_hrv[target_col_hrv]

    X_std_hrv = (X_hrv - X_hrv.mean()) / X_hrv.std()
    X_std_hrv = sm.add_constant(X_std_hrv)

    y_pred_hrv = model.predict(X_std_hrv)
    residuals_hrv = y_hrv - y_pred_hrv

    coef_df_hrv = pd.DataFrame(
        {
            "Feature": ["Intercept"] + [feature_labels[f] for f in feature_cols_hrv],
            "Coefficient": model.params.values,
            "Std Error": model.bse.values,
            "t-value": model.tvalues.values,
            "P-value": model.pvalues.values,
        }
    )

    coef_df_hrv["Significant"] = coef_df_hrv["P-value"] < 0.05
    coef_df_hrv["CI Lower"] = model.conf_int()[0].values
    coef_df_hrv["CI Upper"] = model.conf_int()[1].values

    df_resid_hrv = model.df_resid
    partial_corrs_hrv = []
    for i, feat in enumerate(feature_cols_hrv):
        t_val = model.tvalues.iloc[i + 1]
        partial_r = t_val / np.sqrt(t_val**2 + df_resid_hrv)
        partial_corrs_hrv.append(partial_r)

    partial_corr_df_hrv = pd.DataFrame(
        {
            "Feature": [feature_labels[f] for f in feature_cols_hrv],
            "Partial Correlation": partial_corrs_hrv,
        }
    )

    return {
        "model": model,
        "y": y_hrv,
        "y_pred": y_pred_hrv,
        "residuals": residuals_hrv,
        "coef_df": coef_df_hrv,
        "partial_corr_df": partial_corr_df_hrv,
        "n_observations": len(df_model_hrv),
        "available_optional": available_optional,
    }
