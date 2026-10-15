"""Run the explicitly authorized, fixed Google Calendar test on temporary events.

Usage: python3 scripts/verify_google_calendar.py create|inspect|edit|remove
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from apps.calendar.adapters.google_write import GoogleCalendarWriteError, GoogleCalendarWriter  # noqa: E402
from apps.calendar.service import _provider  # noqa: E402


EXPECTED_CALENDAR_ID = "famordcast@gmail.com"
ZONE = ZoneInfo("America/Tegucigalpa")
PREFIX = "Home Together - prueba "


def stable_id(kind: str) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"home-together/authorized-calendar-test/2026-10-14/{kind}").hex


def timed(day: int, hour: int, minute: int) -> dict:
    start = datetime(2026, 10, day, hour, minute, tzinfo=ZONE)
    return {
        "start": {"dateTime": start.isoformat(), "timeZone": "America/Tegucigalpa"},
        "end": {"dateTime": (start + timedelta(minutes=10)).isoformat(), "timeZone": "America/Tegucigalpa"},
    }


def specs() -> dict[str, dict]:
    common = {"transparency": "transparent", "reminders": {"useDefault": False}}
    return {
        "timed": {
            **common, "id": stable_id("timed"), "summary": PREFIX + "calendario (temporal)",
            **timed(16, 12, 0),
        },
        "all_day": {
            **common, "id": stable_id("all_day"), "summary": PREFIX + "día completo (temporal)",
            "start": {"date": "2026-10-17"}, "end": {"date": "2026-10-18"},
        },
        "recurring": {
            **common, "id": stable_id("recurring"), "summary": PREFIX + "recurrente (temporal)",
            **timed(18, 12, 0), "recurrence": ["RRULE:FREQ=DAILY;COUNT=2"],
        },
    }


def writer() -> GoogleCalendarWriter:
    selected = os.environ.get("HT_GOOGLE_CALENDAR_ID")
    if selected != EXPECTED_CALENDAR_ID:
        raise RuntimeError("El calendario seleccionado no es el destino autorizado")
    return GoogleCalendarWriter(selected, _provider())


def require_ours(event: dict | None) -> dict:
    if not event or not event.get("summary", "").startswith(PREFIX):
        raise RuntimeError("El ID no corresponde a un evento temporal de esta prueba")
    return event


def create(adapter: GoogleCalendarWriter) -> None:
    for kind, body in specs().items():
        existing = adapter.get_event(body["id"])
        if existing:
            require_ours(existing)
            print(f"{kind}: ya existe; no se duplicó")
            continue
        try:
            result = adapter.create_event(body)
        except GoogleCalendarWriteError as error:
            if not error.uncertain and error.http_status != 409:
                raise
            result = adapter.get_event(body["id"])
            if not result:
                raise RuntimeError(f"{kind}: resultado incierto; no repetir la creación") from error
        if result.get("id") != body["id"]:
            raise RuntimeError(f"{kind}: Google devolvió otro ID")
        require_ours(result)
        confirmed = require_ours(adapter.get_event(body["id"]))
        if confirmed.get("start") is None or confirmed.get("end") is None:
            raise RuntimeError(f"{kind}: fechas no confirmadas")
        print(f"{kind}: creado y leído por ID en Google")


def inspect(adapter: GoogleCalendarWriter) -> None:
    for kind, body in specs().items():
        event = adapter.get_event(body["id"])
        if event is None:
            print(f"{kind}: ausente")
            continue
        require_ours(event)
        print(f"{kind}: presente; estado={event.get('status')}; inicio={event.get('start')}; fin={event.get('end')}")
    start = datetime(2026, 10, 18, tzinfo=ZONE)
    result = adapter.events(start, start + timedelta(days=3))
    recurring_id = stable_id("recurring")
    instances = [event for event in result["events"] if event.get("recurringEventId") == recurring_id]
    print(f"recurring: {len(instances)} ocurrencias en la consulta expandida")


def edit(adapter: GoogleCalendarWriter) -> None:
    event_id = stable_id("timed")
    event = require_ours(adapter.get_event(event_id))
    etag = event.get("etag")
    if not etag:
        raise RuntimeError("Google no entregó ETag para editar")
    event["summary"] = PREFIX + "calendario editada (temporal)"
    event.update(timed(16, 12, 15))
    updated = adapter.update_event(event_id, event, etag)
    confirmed = require_ours(adapter.get_event(event_id))
    if confirmed.get("summary") != event["summary"] or confirmed.get("start", {}).get("dateTime") != event["start"]["dateTime"]:
        raise RuntimeError("La edición no quedó confirmada en Google")
    print(f"timed: título y hora editados; mismo ID={updated.get('id') == event_id}")


def remove(adapter: GoogleCalendarWriter) -> None:
    for kind, body in specs().items():
        event = adapter.get_event(body["id"])
        if event is None or event.get("status") == "cancelled":
            print(f"{kind}: ya ausente")
            continue
        require_ours(event)
        etag = event.get("etag")
        if not etag:
            raise RuntimeError(f"{kind}: Google no entregó ETag para eliminar")
        adapter.delete_event(body["id"], etag)
        after = adapter.get_event(body["id"])
        if after is not None and after.get("status") != "cancelled":
            raise RuntimeError(f"{kind}: eliminación no confirmada")
        print(f"{kind}: eliminado; Google devuelve estado cancelled")

    start = datetime(2026, 10, 16, tzinfo=ZONE)
    end = datetime(2026, 10, 21, tzinfo=ZONE)
    test_ids = {body["id"] for body in specs().values()}
    page_token = None
    while True:
        page = adapter.events(start, end, page_token)
        if any(item.get("id") in test_ids or item.get("recurringEventId") in test_ids for item in page["events"]):
            raise RuntimeError("Todavía aparece un evento temporal en la lista activa")
        page_token = page.get("next_page_token")
        if not page_token:
            break
    print("Google events.list: ningún evento temporal activo")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("create", "inspect", "edit", "remove"))
    args = parser.parse_args()
    adapter = writer()
    {"create": create, "inspect": inspect, "edit": edit, "remove": remove}[args.phase](adapter)


if __name__ == "__main__":
    main()
