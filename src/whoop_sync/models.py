from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
import json


@dataclass
class Cycle:
    id: int
    user_id: int
    created_at: str
    updated_at: str
    start: str
    end: str
    timezone_offset: str
    score_state: str
    strain: float = None
    kilojoule: float = None
    average_heart_rate: int = None
    max_heart_rate: int = None


@dataclass
class Recovery:
    cycle_id: int
    sleep_id: str
    user_id: int
    created_at: str
    updated_at: str
    score_state: str
    user_calibrating: bool = None
    recovery_score: int = None
    resting_heart_rate: int = None
    hrv_rmssd_milli: float = None
    spo2_percentage: float = None
    skin_temp_celsius: float = None


@dataclass
class Sleep:
    id: str
    cycle_id: int
    user_id: int
    created_at: str
    updated_at: str
    start: str
    end: str
    timezone_offset: str
    nap: bool
    score_state: str
    total_in_bed_time_milli: int = None
    total_awake_time_milli: int = None
    total_light_sleep_time_milli: int = None
    total_slow_wave_sleep_time_milli: int = None
    total_rem_sleep_time_milli: int = None
    sleep_cycle_count: int = None
    disturbance_count: int = None
    respiratory_rate: float = None
    sleep_performance_percentage: float = None
    sleep_consistency_percentage: float = None
    sleep_efficiency_percentage: float = None


@dataclass
class Workout:
    id: str
    user_id: int
    created_at: str
    updated_at: str
    start: str
    end: str
    timezone_offset: str
    sport_name: str
    sport_id: int
    score_state: str
    strain: float = None
    average_heart_rate: int = None
    max_heart_rate: int = None
    kilojoule: float = None
    percent_recorded: float = None
    distance_meter: float = None
    altitude_gain_meter: float = None
    altitude_change_meter: float = None
    zone_zero_milli: int = None
    zone_one_milli: int = None
    zone_two_milli: int = None
    zone_three_milli: int = None
    zone_four_milli: int = None
    zone_five_milli: int = None


@dataclass
class UserProfile:
    user_id: int
    email: str
    first_name: str
    last_name: str


@dataclass
class BodyMeasurement:
    height_meter: float
    weight_kilogram: float
    max_heart_rate: int


SCHEMA = """
CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    start TEXT,
    end TEXT,
    timezone_offset TEXT,
    score_state TEXT,
    strain REAL,
    kilojoule REAL,
    average_heart_rate INTEGER,
    max_heart_rate INTEGER
);

CREATE TABLE IF NOT EXISTS recoveries (
    cycle_id INTEGER PRIMARY KEY,
    sleep_id TEXT,
    user_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    score_state TEXT,
    user_calibrating INTEGER,
    recovery_score INTEGER,
    resting_heart_rate INTEGER,
    hrv_rmssd_milli REAL,
    spo2_percentage REAL,
    skin_temp_celsius REAL
);

CREATE TABLE IF NOT EXISTS sleeps (
    id TEXT PRIMARY KEY,
    cycle_id INTEGER,
    user_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    start TEXT,
    end TEXT,
    timezone_offset TEXT,
    nap INTEGER,
    score_state TEXT,
    total_in_bed_time_milli INTEGER,
    total_awake_time_milli INTEGER,
    total_light_sleep_time_milli INTEGER,
    total_slow_wave_sleep_time_milli INTEGER,
    total_rem_sleep_time_milli INTEGER,
    sleep_cycle_count INTEGER,
    disturbance_count INTEGER,
    respiratory_rate REAL,
    sleep_performance_percentage REAL,
    sleep_consistency_percentage REAL,
    sleep_efficiency_percentage REAL
);

CREATE TABLE IF NOT EXISTS workouts (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    start TEXT,
    end TEXT,
    timezone_offset TEXT,
    sport_name TEXT,
    sport_id INTEGER,
    score_state TEXT,
    strain REAL,
    average_heart_rate INTEGER,
    max_heart_rate INTEGER,
    kilojoule REAL,
    percent_recorded REAL,
    distance_meter REAL,
    altitude_gain_meter REAL,
    altitude_change_meter REAL,
    zone_zero_milli INTEGER,
    zone_one_milli INTEGER,
    zone_two_milli INTEGER,
    zone_three_milli INTEGER,
    zone_four_milli INTEGER,
    zone_five_milli INTEGER
);

CREATE TABLE IF NOT EXISTS user_profile (
    user_id INTEGER PRIMARY KEY,
    email TEXT,
    first_name TEXT,
    last_name TEXT
);

CREATE TABLE IF NOT EXISTS body_measurement (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    height_meter REAL,
    weight_kilogram REAL,
    max_heart_rate INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cycles_start ON cycles(start);
CREATE INDEX IF NOT EXISTS idx_sleeps_start ON sleeps(start);
CREATE INDEX IF NOT EXISTS idx_workouts_start ON workouts(start);
CREATE INDEX IF NOT EXISTS idx_recoveries_cycle_id ON recoveries(cycle_id);
"""
