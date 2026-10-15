"""Google Calendar API access. OAuth token acquisition lives outside this adapter."""

import json
from datetime import datetime, timedelta
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class GoogleCalendarError(Exception):
    def __init__(self, status: str):
        self.status = status
        super().__init__(status)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class GoogleCalendarReader:
    """Read a selected calendar without storing events or exposing tokens to callers."""

    API_ROOT = "https://www.googleapis.com/calendar/v3"

    def __init__(self, calendar_id: str, access_token: Callable[[], str]):
        if not calendar_id:
            raise ValueError("calendar_id is required")
        self.calendar_id = calendar_id
        self.access_token = access_token
        self._opener = build_opener(_NoRedirect)

    def _get(self, path: str, params: dict | None = None) -> dict:
        query = f"?{urlencode(params)}" if params else ""
        token = self.access_token()
        if not token:
            raise GoogleCalendarError("Sin conexión")
        request = Request(
            f"{self.API_ROOT}{path}{query}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as error:
            raise GoogleCalendarError(f"HTTP {error.code}") from None
        except (URLError, TimeoutError, ValueError):
            raise GoogleCalendarError("Sin conexión") from None

    def calendar_metadata(self) -> dict:
        calendar_id = quote(self.calendar_id, safe="")
        result = self._get(f"/users/me/calendarList/{calendar_id}")
        return {
            "id": result.get("id"),
            "time_zone": result.get("timeZone"),
            "access_role": result.get("accessRole"),
        }

    def available_calendars(self, page_token: str | None = None) -> dict:
        params = {"maxResults": 250}
        if page_token:
            params["pageToken"] = page_token
        result = self._get("/users/me/calendarList", params)
        return {
            "calendars": [{key: item.get(key) for key in (
                "id", "summary", "timeZone", "accessRole", "primary",
            ) if key in item} for item in result.get("items", [])],
            "next_page_token": result.get("nextPageToken"),
        }

    def events(self, start: datetime, end: datetime, page_token: str | None = None) -> dict:
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("An aware start before end is required")
        if end - start > timedelta(days=31):
            raise ValueError("Event window must be 31 days or less")
        calendar_id = quote(self.calendar_id, safe="")
        params = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "timeZone": "America/Tegucigalpa",
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 250,
        }
        if page_token:
            params["pageToken"] = page_token
        result = self._get(f"/calendars/{calendar_id}/events", params)
        return {
            "events": [{key: item.get(key) for key in (
                "id", "etag", "summary", "start", "end", "location",
                "recurringEventId", "originalStartTime", "status", "updated",
            ) if key in item} for item in result.get("items", [])],
            "next_page_token": result.get("nextPageToken"),
            "time_zone": result.get("timeZone"),
        }
