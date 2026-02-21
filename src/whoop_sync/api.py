from typing import Optional, List, Dict, Any, Generator
import requests
from datetime import datetime

from .config import config
from .auth import WhoopAuth


class WhoopAPI:
    def __init__(self, auth: WhoopAuth):
        self.auth = auth
        self.base_url = config.api_base_url

    def _headers(self) -> dict:
        token = self.auth.get_valid_access_token()
        if not token:
            raise Exception("No valid access token")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self._headers(), params=params)

        if response.status_code == 401:
            if self.auth.refresh_access_token():
                response = requests.get(url, headers=self._headers(), params=params)

        response.raise_for_status()
        return response.json()

    def _paginate(
        self, endpoint: str, params: dict = None, key: str = "records"
    ) -> Generator[List[Dict], None, None]:
        if params is None:
            params = {}

        params["limit"] = params.get("limit", 25)

        while True:
            data = self._get(endpoint, params)
            records = data.get(key, [])

            if records:
                yield records

            next_token = data.get("next_token")
            if not next_token:
                break

            params["nextToken"] = next_token

    def get_profile(self) -> dict:
        return self._get("/developer/v2/user/profile/basic")

    def get_body_measurement(self) -> dict:
        return self._get("/developer/v2/user/measurement/body")

    def get_cycles(
        self, start: datetime = None, end: datetime = None
    ) -> Generator[List[Dict], None, None]:
        params = {}
        if start:
            params["start"] = start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if end:
            params["end"] = end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        yield from self._paginate("/developer/v2/cycle", params)

    def get_recoveries(
        self, start: datetime = None, end: datetime = None
    ) -> Generator[List[Dict], None, None]:
        params = {}
        if start:
            params["start"] = start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if end:
            params["end"] = end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        yield from self._paginate("/developer/v2/recovery", params)

    def get_sleeps(
        self, start: datetime = None, end: datetime = None
    ) -> Generator[List[Dict], None, None]:
        params = {}
        if start:
            params["start"] = start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if end:
            params["end"] = end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        yield from self._paginate("/developer/v2/activity/sleep", params)

    def get_workouts(
        self, start: datetime = None, end: datetime = None
    ) -> Generator[List[Dict], None, None]:
        params = {}
        if start:
            params["start"] = start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if end:
            params["end"] = end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        yield from self._paginate("/developer/v2/activity/workout", params)
