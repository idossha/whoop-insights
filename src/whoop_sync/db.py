import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

from .config import config
from .models import SCHEMA


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.db_path
        self.conn = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def upsert_cycle(self, cycle: dict):
        score = cycle.get("score") or {}
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO cycles 
            (id, user_id, created_at, updated_at, start, end, timezone_offset, 
             score_state, strain, kilojoule, average_heart_rate, max_heart_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                cycle["id"],
                cycle["user_id"],
                cycle["created_at"],
                cycle["updated_at"],
                cycle["start"],
                cycle.get("end"),
                cycle.get("timezone_offset"),
                cycle["score_state"],
                score.get("strain"),
                score.get("kilojoule"),
                score.get("average_heart_rate"),
                score.get("max_heart_rate"),
            ),
        )
        conn.commit()

    def upsert_recovery(self, recovery: dict):
        score = recovery.get("score") or {}
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO recoveries 
            (cycle_id, sleep_id, user_id, created_at, updated_at, score_state,
             user_calibrating, recovery_score, resting_heart_rate, hrv_rmssd_milli,
             spo2_percentage, skin_temp_celsius)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                recovery["cycle_id"],
                recovery["sleep_id"],
                recovery["user_id"],
                recovery["created_at"],
                recovery["updated_at"],
                recovery["score_state"],
                1 if score.get("user_calibrating") else 0,
                score.get("recovery_score"),
                score.get("resting_heart_rate"),
                score.get("hrv_rmssd_milli"),
                score.get("spo2_percentage"),
                score.get("skin_temp_celsius"),
            ),
        )
        conn.commit()

    def upsert_sleep(self, sleep: dict):
        score = sleep.get("score") or {}
        stage = score.get("stage_summary") or {}
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO sleeps 
            (id, cycle_id, user_id, created_at, updated_at, start, end, 
             timezone_offset, nap, score_state, total_in_bed_time_milli,
             total_awake_time_milli, total_light_sleep_time_milli,
             total_slow_wave_sleep_time_milli, total_rem_sleep_time_milli,
             sleep_cycle_count, disturbance_count, respiratory_rate,
             sleep_performance_percentage, sleep_consistency_percentage,
             sleep_efficiency_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                sleep["id"],
                sleep.get("cycle_id"),
                sleep["user_id"],
                sleep["created_at"],
                sleep["updated_at"],
                sleep["start"],
                sleep.get("end"),
                sleep.get("timezone_offset"),
                1 if sleep.get("nap") else 0,
                sleep["score_state"],
                stage.get("total_in_bed_time_milli"),
                stage.get("total_awake_time_milli"),
                stage.get("total_light_sleep_time_milli"),
                stage.get("total_slow_wave_sleep_time_milli"),
                stage.get("total_rem_sleep_time_milli"),
                stage.get("sleep_cycle_count"),
                stage.get("disturbance_count"),
                score.get("respiratory_rate"),
                score.get("sleep_performance_percentage"),
                score.get("sleep_consistency_percentage"),
                score.get("sleep_efficiency_percentage"),
            ),
        )
        conn.commit()

    def upsert_workout(self, workout: dict):
        score = workout.get("score") or {}
        zones = score.get("zone_durations") or {}
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO workouts 
            (id, user_id, created_at, updated_at, start, end, timezone_offset,
             sport_name, sport_id, score_state, strain, average_heart_rate,
             max_heart_rate, kilojoule, percent_recorded, distance_meter,
             altitude_gain_meter, altitude_change_meter, zone_zero_milli,
             zone_one_milli, zone_two_milli, zone_three_milli, zone_four_milli,
             zone_five_milli)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                workout["id"],
                workout["user_id"],
                workout["created_at"],
                workout["updated_at"],
                workout["start"],
                workout.get("end"),
                workout.get("timezone_offset"),
                workout.get("sport_name"),
                workout.get("sport_id"),
                workout["score_state"],
                score.get("strain"),
                score.get("average_heart_rate"),
                score.get("max_heart_rate"),
                score.get("kilojoule"),
                score.get("percent_recorded"),
                score.get("distance_meter"),
                score.get("altitude_gain_meter"),
                score.get("altitude_change_meter"),
                zones.get("zone_zero_milli"),
                zones.get("zone_one_milli"),
                zones.get("zone_two_milli"),
                zones.get("zone_three_milli"),
                zones.get("zone_four_milli"),
                zones.get("zone_five_milli"),
            ),
        )
        conn.commit()

    def upsert_profile(self, profile: dict):
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO user_profile (user_id, email, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """,
            (
                profile["user_id"],
                profile["email"],
                profile["first_name"],
                profile["last_name"],
            ),
        )
        conn.commit()

    def upsert_body_measurement(self, measurement: dict):
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO body_measurement 
            (id, height_meter, weight_kilogram, max_heart_rate, updated_at)
            VALUES (1, ?, ?, ?, ?)
        """,
            (
                measurement.get("height_meter"),
                measurement.get("weight_kilogram"),
                measurement.get("max_heart_rate"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()

    def get_latest_cycle_date(self) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute("SELECT MAX(start) FROM cycles").fetchone()
        return row[0] if row and row[0] else None

    def get_latest_sleep_date(self) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute("SELECT MAX(start) FROM sleeps").fetchone()
        return row[0] if row and row[0] else None

    def get_latest_workout_date(self) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute("SELECT MAX(start) FROM workouts").fetchone()
        return row[0] if row and row[0] else None

    def get_latest_recovery_date(self) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute("""
            SELECT MAX(r.updated_at) FROM recoveries r
        """).fetchone()
        return row[0] if row and row[0] else None

    def get_stats(self) -> dict:
        conn = self._get_conn()
        stats = {}

        for table in ["cycles", "recoveries", "sleeps", "workouts"]:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            stats[table] = row[0]

        return stats
