# WHOOP Recovery & HRV Prediction Model

## Objective

Predict next-day physiological metrics using data available at the end of the current day:
1. **Recovery Score** (0-100%) - WHOOP's proprietary measure of readiness
2. **HRV (ms)** - Heart Rate Variability (RMSSD), a direct physiological measurement

## WHOOP Data Model Overview

### Physiological Cycle (Core Concept)

WHOOP organizes data around **Physiological Cycles**, not calendar days:

```
Cycle N: Wake (Day N) ────── Activity ────── Sleep ────── Wake (Day N+1)
         │                                          │
         └── Cycle N starts                         └── Cycle N ends
             (end of sleep N)                           (end of sleep N+1)
```

**Key insight**: A cycle starts when you wake up and ends when you wake up the next day.

### Entity Relationships

| Entity | Relationship | Meaning |
|--------|--------------|---------|
| **Sleep** | `sleep.cycle_id = cycle.id` | The sleep that ENDS when this cycle starts (previous night's sleep) |
| **Recovery** | `recovery.cycle_id = cycle.id` | How recovered you are FOR this cycle (calculated at cycle start) |
| **Cycle Score** | Embedded in cycle | Strain/activity during this cycle (the entire waking day) |
| **Workout** | Temporal | Falls within a cycle's time range (during the day) |

### Temporal Flow Example

```
                    JAN 31 (Night)      FEB 1 (Day)        FEB 1 (Night)      FEB 2 (Day)
                         │                   │                   │                   │
                    ┌────┴────┐         ┌────┴────┐         ┌────┴────┐              │
                    │ Sleep N │         │ Cycle N │         │Sleep N+1│              │
                    │ (92%)   │────────▶│         │────────▶│ (84%)   │              │
                    └─────────┘         │ Strain: │         └─────────┘              │
                                        │   5.6   │              │                    │
                                        │ Rec: 55 │              │                    │
                                        │ HRV: 56 │◀─────────────┘                    │
                                        │         │         Determines               │
                                        │ Workout │      Recovery N+1=51             │
                                        │ weights │                                  │
                                        └─────────┘                                  │
```

## Prediction Logic

### What We Predict
- **Target**: Recovery Score and HRV for Cycle N+1 (next morning's metrics)

### What We Use as Features (all available at end of Cycle N)

| Feature Category | Variables | Source | Why It Matters |
|-----------------|-----------|--------|----------------|
| **Cycle Activity** | strain, kilojoules, avg_hr, max_hr | `cycles.score` | Daily cardiovascular load affects next-day recovery |
| **Current Recovery** | recovery_score, hrv, resting_hr, spo2, skin_temp | `recoveries.score` | Baseline state - recovery tends to autocorrelate |
| **Previous Sleep** | performance%, efficiency%, hours, SWS, REM, disturbances | `sleeps.score` | Sleep quality from last night (determined current recovery) |
| **Workouts** | count, total strain, kilojoules, heart rates | `workouts` | Training load on current day |

### Why Sleep N+1 is NOT a Feature

The sleep that determines Recovery N+1 (Sleep N+1, the night between Day N and Day N+1) **has not occurred yet** at prediction time. We predict at the **end of Day N**, before the person goes to sleep.

This is the key constraint: we can only use data available before the target sleep happens.

## Feature Engineering Details

### From Cycles
```sql
c.strain           -- Total cardiovascular strain for the day (0-21 scale)
c.kilojoule        -- Total energy expenditure
c.average_heart_rate
c.max_heart_rate
```

### From Recovery (baseline state)
```sql
r.recovery_score      -- Current day's recovery (0-100%)
r.hrv_rmssd_milli     -- Current HRV in milliseconds
r.resting_heart_rate  -- RHR
r.spo2_percentage     -- Blood oxygen (4.0 devices)
r.skin_temp_celsius   -- Skin temperature (4.0 devices)
```

### From Sleep (last night's quality)
```sql
s.sleep_performance_percentage  -- How well you met sleep need
s.sleep_efficiency_percentage   -- Time asleep vs time in bed
s.sleep_consistency_percentage  -- Same time vs previous days
s.total_in_bed_time_milli       -- Duration (converted to hours)
s.total_slow_wave_sleep_time_milli  -- Deep sleep (physical recovery)
s.total_rem_sleep_time_milli        -- REM sleep (mental recovery)
s.total_light_sleep_time_milli      -- Light sleep
s.total_awake_time_milli            -- Wake periods
s.sleep_cycle_count                 -- Number of sleep cycles
s.disturbance_count                 -- Sleep interruptions
s.respiratory_rate                  -- Breathing rate during sleep
```

### From Workouts (training load)
```sql
COUNT(*)                -- Number of workouts
SUM(strain)            -- Total workout strain
SUM(kilojoule)         -- Total energy burned
AVG(average_heart_rate)
MAX(max_heart_rate)
```

## Model Architecture

We use **Ridge Regression** (L2 regularized linear regression) because:
1. Small dataset (~21 samples) - regularization prevents overfitting
2. Interpretable coefficients - understand what drives recovery
3. Handles correlated features (e.g., strain and kilojoules)

## Evaluation

Due to limited data, we use:
- **5-Fold Cross-Validation** for robust R² estimation
- **Bootstrap 95% Confidence Intervals** for coefficient uncertainty
- **MAE (Mean Absolute Error)** for practical interpretability

## Limitations

1. **Sample Size**: 21 days of data limits model complexity and generalizability
2. **Missing Sleep N+1**: Cannot directly use the sleep data that determines target recovery
3. **Single User**: Model trained on one person's data
4. **No External Factors**: Diet, stress, illness, alcohol not captured
5. **Same-Day Prediction**: Cannot predict same-day recovery (only next-day)

## Future Improvements

1. **Lagged Features**: Add 2-3 day rolling averages (7-day strain, sleep debt)
2. **Day of Week**: Capture weekly patterns (weekend vs weekday)
3. **Cumulative Load**: Rolling strain totals
4. **More Data**: Pool multiple users or collect longer history
5. **Non-linear Models**: Try gradient boosting if data volume increases
