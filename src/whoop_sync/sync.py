from datetime import datetime, timedelta
from typing import Optional, Callable, Generator, List, Dict

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

    def _sync_entity(
        self,
        label: str,
        get_latest_date: Callable[[], Optional[str]],
        fetch: Callable[[Optional[datetime], Optional[datetime]], Generator[List[Dict], None, None]],
        upsert: Callable[[dict], None],
        start: datetime = None,
        end: datetime = None,
        full_sync: bool = False,
    ):
        if not full_sync and start is None:
            latest = get_latest_date()
            if latest:
                start = datetime.fromisoformat(latest.replace("Z", "+00:00"))
                start = start - timedelta(days=1)

        print(f"Syncing {label} from {start or 'beginning'}...")
        count = 0
        for records in fetch(start=start, end=end):
            for record in records:
                upsert(record)
                count += 1
        print(f"  Synced {count} {label}")

    def sync_cycles(self, start: datetime = None, end: datetime = None, full_sync: bool = False):
        self._sync_entity(
            "cycles",
            self.db.get_latest_cycle_date,
            self.api.get_cycles,
            self.db.upsert_cycle,
            start=start, end=end, full_sync=full_sync,
        )

    def sync_recoveries(self, start: datetime = None, end: datetime = None, full_sync: bool = False):
        self._sync_entity(
            "recoveries",
            self.db.get_latest_recovery_date,
            self.api.get_recoveries,
            self.db.upsert_recovery,
            start=start, end=end, full_sync=full_sync,
        )

    def sync_sleeps(self, start: datetime = None, end: datetime = None, full_sync: bool = False):
        self._sync_entity(
            "sleeps",
            self.db.get_latest_sleep_date,
            self.api.get_sleeps,
            self.db.upsert_sleep,
            start=start, end=end, full_sync=full_sync,
        )

    def sync_workouts(self, start: datetime = None, end: datetime = None, full_sync: bool = False):
        self._sync_entity(
            "workouts",
            self.db.get_latest_workout_date,
            self.api.get_workouts,
            self.db.upsert_workout,
            start=start, end=end, full_sync=full_sync,
        )

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
