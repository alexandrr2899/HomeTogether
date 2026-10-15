"""Write to the selected Google Calendar with stable IDs and version checks."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request

from .google import GoogleCalendarError, GoogleCalendarReader


class GoogleCalendarWriteError(GoogleCalendarError):
    def __init__(self, status: str, http_status: int | None = None, uncertain: bool = False):
        super().__init__(status)
        self.http_status = http_status
        self.uncertain = uncertain


class GoogleCalendarWriter(GoogleCalendarReader):
    """A narrow event writer; callers must select a calendar and retain event IDs."""

    def _event_path(self, event_id: str | None = None) -> str:
        path = f"/calendars/{quote(self.calendar_id, safe='')}/events"
        if event_id is not None:
            if not event_id or "/" in event_id or len(event_id) > 1024:
                raise ValueError("event_id is invalid")
            path += f"/{quote(event_id, safe='')}"
        return path

    def _send(self, method: str, path: str, payload: dict | None = None, etag: str | None = None) -> dict:
        token = self.access_token()
        if not token:
            raise GoogleCalendarWriteError("Sin conexión")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if etag:
            headers["If-Match"] = etag
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, separators=(",", ":")).encode()
        request = Request(f"{self.API_ROOT}{path}", data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=20) as response:
                body = response.read()
            return json.loads(body) if body else {}
        except HTTPError as error:
            raise GoogleCalendarWriteError(f"Google respondió HTTP {error.code}", http_status=error.code) from None
        except (URLError, TimeoutError, ValueError):
            raise GoogleCalendarWriteError(
                "Resultado incierto; consulta el evento por su ID antes de intentar de nuevo", uncertain=True
            ) from None

    def get_event(self, event_id: str) -> dict | None:
        try:
            return self._send("GET", self._event_path(event_id))
        except GoogleCalendarWriteError as error:
            if error.http_status == 404:
                return None
            raise

    def create_event(self, event: dict) -> dict:
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("A stable event ID is required")
        if not event.get("summary") or not event.get("start") or not event.get("end"):
            raise ValueError("Event title, start and end are required")
        return self._send("POST", self._event_path(), event)

    def update_event(self, event_id: str, event: dict, etag: str) -> dict:
        if not etag or event.get("id") != event_id:
            raise ValueError("A matching event ID and ETag are required")
        return self._send("PUT", self._event_path(event_id), event, etag)

    def delete_event(self, event_id: str, etag: str) -> None:
        if not etag:
            raise ValueError("An ETag is required")
        self._send("DELETE", self._event_path(event_id), etag=etag)
