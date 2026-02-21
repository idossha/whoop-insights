from datetime import datetime, timedelta
from typing import Optional

from .auth import WhoopAuth
from .api import WhoopAPI
from .db import Database


class WhoopSync:
    def __init__(self):
        self.auth = WhoopAuth()
        self.api = None
        self.db = Database()

    def authenticate(self) -> bool:
        if self.auth.load_tokens():
            if self.auth.is_authenticated():
                self.api = WhoopAPI(self.auth)
                return True

        if not self.auth.authorize():
            return False

        self.api = WhoopAPI(self.auth)
        return True

    def sync_profile(self):
        print("Syncing profile...")
        profile = self.api.get_profile()
        self.db.upsert_profile(profile)
        print(f"  User: {profile.get('first_name')} {profile.get('last_name')}")

    def sync_body_measurement(self):
        print("Syncing body measurements...")
        measurement = self.api.get_body_measurement()
        self.db.upsert_body_measurement(measurement)
        print(
            f"  Height: {measurement.get('height_meter')}m, Weight: {measurement.get('weight_kilogram')}kg"
        )

    def sync_cycles(
        self, start: datetime = None, end: datetime = None, full_sync: bool = False
    ):
        if not full_sync and start is None:
            latest = self.db.get_latest_cycle_date()
            if latest:
                start = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                start = start - timedelta(days=1)

        print(f"Syncing cycles from {start or 'beginning'}...")
        count = 0
        for records in self.api.get_cycles(start=start, end=end):
            for cycle in records:
                self.db.upsert_cycle(cycle)
                count += 1
        print(f"  Synced {count} cycles")

    def sync_recoveries(
        self, start: datetime = None, end: datetime = None, full_sync: bool = False
    ):
        if not full_sync and start is None:
            latest = self.db.get_latest_recovery_date()
            if latest:
                start = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                start = start - timedelta(days=1)

        print(f"Syncing recoveries from {start or 'beginning'}...")
        count = 0
        for records in self.api.get_recoveries(start=start, end=end):
            for recovery in records:
                self.db.upsert_recovery(recovery)
                count += 1
        print(f"  Synced {count} recoveries")

    def sync_sleeps(
        self, start: datetime = None, end: datetime = None, full_sync: bool = False
    ):
        if not full_sync and start is None:
            latest = self.db.get_latest_sleep_date()
            if latest:
                start = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                start = start - timedelta(days=1)

        print(f"Syncing sleeps from {start or 'beginning'}...")
        count = 0
        for records in self.api.get_sleeps(start=start, end=end):
            for sleep in records:
                self.db.upsert_sleep(sleep)
                count += 1
        print(f"  Synced {count} sleeps")

    def sync_workouts(
        self, start: datetime = None, end: datetime = None, full_sync: bool = False
    ):
        if not full_sync and start is None:
            latest = self.db.get_latest_workout_date()
            if latest:
                start = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                start = start - timedelta(days=1)

        print(f"Syncing workouts from {start or 'beginning'}...")
        count = 0
        for records in self.api.get_workouts(start=start, end=end):
            for workout in records:
                self.db.upsert_workout(workout)
                count += 1
        print(f"  Synced {count} workouts")

    def sync_all(
        self, full_sync: bool = False, start: datetime = None, end: datetime = None
    ):
        self.sync_profile()
        self.sync_body_measurement()
        self.sync_cycles(start=start, end=end, full_sync=full_sync)
        self.sync_recoveries(start=start, end=end, full_sync=full_sync)
        self.sync_sleeps(start=start, end=end, full_sync=full_sync)
        self.sync_workouts(start=start, end=end, full_sync=full_sync)

        stats = self.db.get_stats()
        print(f"\nDatabase stats:")
        for table, count in stats.items():
            print(f"  {table}: {count} records")

    def close(self):
        self.db.close()
