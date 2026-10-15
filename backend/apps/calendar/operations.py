"""Application operations for the selected Google calendar; Google is the source of truth."""

import hashlib
import hmac

from django.conf import settings

from .adapters.google import GoogleCalendarError
from .adapters.google_write import GoogleCalendarWriteError
from .service import calendar_writer


PUBLIC_FIELDS = (
    "id", "etag", "summary", "start", "end", "description", "location",
    "recurrence", "recurringEventId", "originalStartTime", "status", "updated",
)


class CalendarOperationError(Exception):
    def __init__(self, detail: str, status_code: int):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def public_event(event: dict) -> dict:
    return {key: event[key] for key in PUBLIC_FIELDS if key in event}


def _writer():
    writer = calendar_writer()
    if writer is None:
        raise CalendarOperationError("Google Calendar sin configurar", 503)
    try:
        metadata = writer.calendar_metadata()
    except GoogleCalendarError:
        raise CalendarOperationError("No se pudo comprobar el permiso del calendario", 503) from None
    if metadata.get("id") != writer.calendar_id or metadata.get("access_role") not in {"owner", "writer"}:
        raise CalendarOperationError("La cuenta ya no puede escribir en el calendario seleccionado", 403)
    return writer


def _event_id(operation_id, user_id: int, calendar_id: str) -> str:
    value = f"calendar:{calendar_id}:user:{user_id}:operation:{operation_id}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), value, hashlib.sha256).hexdigest()[:32]


def _matches(event: dict, expected: dict) -> bool:
    return event.get("status") != "cancelled" and all(
        (event.get(key, "") if value == "" else event.get(key)) == value
        for key, value in expected.items() if key != "id"
    )


def _google_error(error: GoogleCalendarWriteError) -> CalendarOperationError:
    if error.http_status == 412:
        return CalendarOperationError("El evento cambió en Google; actualiza la agenda", 409)
    if error.http_status == 404:
        return CalendarOperationError("Evento no encontrado", 404)
    if error.http_status == 403:
        return CalendarOperationError("Google rechazó el permiso de escritura", 403)
    if error.http_status == 400:
        return CalendarOperationError("Google rechazó los datos del evento", 400)
    return CalendarOperationError("No se pudo confirmar el cambio en Google", 503)


def create_event(data: dict, user_id: int) -> dict:
    writer = _writer()
    event_id = _event_id(data["operation_id"], user_id, writer.calendar_id)
    body = {key: value for key, value in data.items() if key != "operation_id"}
    body["id"] = event_id
    try:
        existing = writer.get_event(event_id)
        if existing is not None:
            if _matches(existing, body):
                return public_event(existing)
            raise CalendarOperationError("La operación ya tiene otro resultado; inicia una nueva", 409)
        try:
            created = writer.create_event(body)
        except GoogleCalendarWriteError as error:
            if not error.uncertain and error.http_status != 409:
                raise _google_error(error) from None
            # Google may have committed the request before a timeout. Read the
            # stable ID, and never blindly issue a second POST.
            existing = writer.get_event(event_id)
            if existing is None:
                raise CalendarOperationError("Resultado incierto; vuelve a consultar antes de intentar otra vez", 503) from None
            if not _matches(existing, body):
                raise CalendarOperationError("La operación ya tiene otro resultado; inicia una nueva", 409)
            created = existing
    except GoogleCalendarWriteError as error:
        raise _google_error(error) from None
    except GoogleCalendarError:
        raise CalendarOperationError("No se pudo conectar con Google Calendar", 503) from None
    if created.get("id") != event_id:
        raise CalendarOperationError("Google devolvió un identificador inesperado", 503)
    return public_event(created)


def read_event(event_id: str) -> dict:
    writer = calendar_writer()
    if writer is None:
        raise CalendarOperationError("Google Calendar sin configurar", 503)
    try:
        event = writer.get_event(event_id)
    except GoogleCalendarWriteError as error:
        raise _google_error(error) from None
    except GoogleCalendarError:
        raise CalendarOperationError("No se pudo conectar con Google Calendar", 503) from None
    if event is None or event.get("status") == "cancelled":
        raise CalendarOperationError("Evento no encontrado", 404)
    return public_event(event)


def update_event(event_id: str, changes: dict, etag: str) -> dict:
    writer = _writer()
    try:
        current = writer.get_event(event_id)
        if current is None or current.get("status") == "cancelled":
            raise CalendarOperationError("Evento no encontrado", 404)
        if current.get("etag") != etag:
            raise CalendarOperationError("El evento cambió en Google; actualiza la agenda", 409)
        replacement = {**current, **changes}
        try:
            updated = writer.update_event(event_id, replacement, etag)
        except GoogleCalendarWriteError as error:
            if not error.uncertain:
                raise _google_error(error) from None
            latest = writer.get_event(event_id)
            if latest is None or not _matches(latest, changes):
                raise CalendarOperationError("Resultado incierto; actualiza la agenda antes de intentar otra vez", 503) from None
            updated = latest
    except GoogleCalendarWriteError as error:
        raise _google_error(error) from None
    except GoogleCalendarError:
        raise CalendarOperationError("No se pudo conectar con Google Calendar", 503) from None
    return public_event(updated)


def delete_event(event_id: str, etag: str) -> None:
    writer = _writer()
    try:
        current = writer.get_event(event_id)
        if current is None or current.get("status") == "cancelled":
            return
        if current.get("etag") != etag:
            raise CalendarOperationError("El evento cambió en Google; actualiza la agenda", 409)
        try:
            writer.delete_event(event_id, etag)
        except GoogleCalendarWriteError as error:
            if not error.uncertain:
                raise _google_error(error) from None
        latest = writer.get_event(event_id)
        if latest is not None and latest.get("status") != "cancelled":
            raise CalendarOperationError("Resultado incierto; el evento sigue visible en Google", 503)
    except GoogleCalendarWriteError as error:
        raise _google_error(error) from None
    except GoogleCalendarError:
        raise CalendarOperationError("No se pudo conectar con Google Calendar", 503) from None
