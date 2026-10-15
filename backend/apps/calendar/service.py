"""Construct the direct Google Calendar adapter from server-side OAuth settings."""

import os
from functools import lru_cache

from .adapters.google import GoogleCalendarReader
from .adapters.google_write import GoogleCalendarWriter
from .adapters.oauth import RefreshTokenProvider


@lru_cache(maxsize=1)
def _provider() -> RefreshTokenProvider:
    return RefreshTokenProvider(
        os.environ["HT_GOOGLE_CLIENT_ID"],
        os.environ["HT_GOOGLE_CLIENT_SECRET"],
        os.environ["HT_GOOGLE_REFRESH_TOKEN"],
    )


def calendar_reader(calendar_id: str | None = None) -> GoogleCalendarReader | None:
    selected_id = calendar_id or os.environ.get("HT_GOOGLE_CALENDAR_ID", "")
    if not selected_id or not all(os.environ.get(key) for key in (
        "HT_GOOGLE_CLIENT_ID", "HT_GOOGLE_CLIENT_SECRET", "HT_GOOGLE_REFRESH_TOKEN",
    )):
        return None
    return GoogleCalendarReader(selected_id, _provider())


def calendar_writer() -> GoogleCalendarWriter | None:
    reader = calendar_reader()
    if reader is None:
        return None
    return GoogleCalendarWriter(reader.calendar_id, _provider())
