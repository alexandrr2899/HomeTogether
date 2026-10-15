"""Read configured external lists directly; Home Assistant remains the bridge."""

import os

from apps.integrations.adapters.home_assistant import HomeAssistantClient, HomeAssistantError, configured_home_assistant_client


LISTS = (
    ("compras", "Compras", "HT_LIST_COMPRAS_ENTITY_ID"),
    ("super", "Súper", "HT_LIST_SUPER_ENTITY_ID"),
    ("tareas", "To-do", "HT_LIST_TASKS_ENTITY_ID"),
)


def configured_client() -> HomeAssistantClient:
    return configured_home_assistant_client()


def entity_for_list(list_id: str) -> str:
    entry = next((row for row in LISTS if row[0] == list_id), None)
    if entry is None:
        raise ValueError("Lista desconocida")
    entity_id = os.environ.get(entry[2], "")
    if not entity_id:
        raise ValueError("Lista sin configurar")
    return entity_id


def items_for_entity(client: HomeAssistantClient, entity_id: str) -> list[dict]:
    return [item for status in ("needs_action", "completed") for item in client.todo_items(entity_id, status)]


def read_lists() -> list[dict]:
    output = []
    try:
        client = configured_client()
    except (KeyError, ValueError):
        client = None

    for list_id, name, env_name in LISTS:
        entity_id = os.environ.get(env_name, "")
        entry = {"id": list_id, "name": name, "entity_id": entity_id or None, "origin": "alexa_devices", "items": []}
        if not entity_id or client is None:
            entry["status"] = "Sin configurar"
        else:
            try:
                items = items_for_entity(client, entity_id)
                entry["items"] = [
                    {key: item.get(key) for key in ("uid", "summary", "status", "due") if key in item}
                    for item in items
                ]
                entry["status"] = "Conectado"
            except HomeAssistantError:
                entry["status"] = "Sin conexión"
        output.append(entry)
    return output
