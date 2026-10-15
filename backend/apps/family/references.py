"""Resolve family references against the original calendar or task list."""

from apps.calendar.operations import CalendarOperationError, read_event
from apps.integrations.adapters.home_assistant import HomeAssistantError
from apps.lists.service import configured_client, entity_for_list, items_for_entity


def resolve_reference(source: str, external_id: str) -> dict:
    if source == "google_calendar":
        try:
            event = read_event(external_id)
        except CalendarOperationError as error:
            return {"status": "Sin datos" if error.status_code == 404 else "Sin conexión"}
        return {"status": "Conectado", "title": event.get("summary") or "Sin título",
                "kind": "evento", "start": event.get("start")}

    if source == "home_assistant_todo":
        list_id, separator, uid = external_id.partition(":")
        if separator != ":" or list_id != "tareas" or not uid:
            return {"status": "Sin configurar"}
        try:
            items = items_for_entity(configured_client(), entity_for_list(list_id))
        except (KeyError, ValueError):
            return {"status": "Sin configurar"}
        except HomeAssistantError:
            return {"status": "Sin conexión"}
        item = next((item for item in items if item.get("uid") == uid), None)
        if item is None:
            # Alexa may omit completed items from Home Assistant even while they
            # still exist in its app. Absence here is not proof of deletion.
            return {"status": "Sin datos"}
        return {"status": "Conectado", "title": item.get("summary") or "Sin título",
                "kind": "tarea", "item_status": item.get("status")}

    return {"status": "Sin configurar"}
