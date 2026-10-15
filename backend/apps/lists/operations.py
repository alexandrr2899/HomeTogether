"""Confirmed mutations of existing Home Assistant to-do entities."""

import time

from apps.integrations.adapters.home_assistant import HomeAssistantError

from .models import ListCreateOperation
from .service import configured_client, entity_for_list, items_for_entity


FEATURES = {"add_item": 1, "remove_item": 2, "update_item": 4}


class ListOperationError(Exception):
    def __init__(self, detail: str, status_code: int = 503):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _context(list_id: str, action: str):
    try:
        entity_id = entity_for_list(list_id)
        client = configured_client()
        state = client.get(f"/api/states/{entity_id}")
    except ValueError:
        raise ListOperationError("Lista sin configurar", 503) from None
    except HomeAssistantError:
        raise ListOperationError("No se pudo consultar Home Assistant", 503) from None
    if not isinstance(state, dict) or state.get("entity_id") != entity_id:
        raise ListOperationError("La entidad de lista no está disponible", 503)
    features = state.get("attributes", {}).get("supported_features")
    if not isinstance(features, int) or not (features & FEATURES[action]):
        raise ListOperationError("Esta lista no admite esa operación", 409)
    return client, entity_id


def _items(client, entity_id):
    try:
        return items_for_entity(client, entity_id)
    except HomeAssistantError:
        raise ListOperationError("No se pudo consultar la lista", 503) from None


def _confirmed_item(client, entity_id, predicate):
    for attempt in range(3):
        try:
            matches = [item for item in items_for_entity(client, entity_id) if predicate(item)]
            if len(matches) == 1:
                return matches[0]
        except HomeAssistantError:
            pass
        if attempt < 2:
            time.sleep(0.5)
    return None


def _matching_new_item(operation, items):
    initial = set(operation.initial_uids)
    matches = [item for item in items if item.get("uid") not in initial and
               item.get("summary", "").casefold() == operation.summary.casefold()]
    return matches[0] if len(matches) == 1 else None


def _confirmed_new_item(client, entity_id, operation):
    for attempt in range(3):
        try:
            item = _matching_new_item(operation, items_for_entity(client, entity_id))
            if item:
                return item
        except HomeAssistantError:
            pass
        if attempt < 2:
            time.sleep(0.5)
    return None


def create_item(list_id: str, operation_id, summary: str, actor):
    client, entity_id = _context(list_id, "add_item")
    operation = ListCreateOperation.objects.filter(pk=operation_id).first()
    if operation:
        if operation.actor_id != actor.pk or operation.list_id != list_id or operation.summary != summary:
            raise ListOperationError("La operación ya se usó para otro ítem", 409)
        if operation.state == "confirmed":
            item = _confirmed_item(client, entity_id, lambda row: row.get("uid") == operation.external_uid)
            if item:
                return item
            raise ListOperationError("El ítem cambió fuera de Home Together; actualiza la lista", 409)
        item = _confirmed_new_item(client, entity_id, operation)
        if item:
            operation.external_uid = item["uid"]
            operation.state = "confirmed"
            operation.save(update_fields=["external_uid", "state", "updated_at"])
            return item
        raise ListOperationError("Resultado incierto; actualiza la lista antes de crear de nuevo", 409)

    before = _items(client, entity_id)
    if any(item.get("summary", "").casefold() == summary.casefold() for item in before):
        raise ListOperationError("Ya hay un ítem con ese nombre en la lista", 409)
    operation = ListCreateOperation.objects.create(
        id=operation_id, actor=actor, list_id=list_id, summary=summary,
        initial_uids=[item["uid"] for item in before if item.get("uid")],
    )
    try:
        client.todo_action("add_item", entity_id, item=summary)
    except HomeAssistantError:
        pass  # The request may have reached Home Assistant; read before reporting failure.
    item = _confirmed_new_item(client, entity_id, operation)
    if item:
        operation.external_uid = item["uid"]
        operation.state = "confirmed"
        operation.save(update_fields=["external_uid", "state", "updated_at"])
        return item
    operation.state = "uncertain"
    operation.save(update_fields=["state", "updated_at"])
    raise ListOperationError("No se pudo confirmar la creación; actualiza la lista antes de reintentar", 503)


def update_item(list_id: str, uid: str, changes: dict):
    client, entity_id = _context(list_id, "update_item")
    before = next((item for item in _items(client, entity_id) if item.get("uid") == uid), None)
    if before is None:
        raise ListOperationError("El ítem ya no está disponible; actualiza la lista", 409)
    fields = {"item": uid}
    if "summary" in changes:
        fields["rename"] = changes["summary"]
    if "status" in changes:
        fields["status"] = changes["status"]
    try:
        client.todo_action("update_item", entity_id, **fields)
    except HomeAssistantError:
        pass
    def matches(item):
        return item.get("uid") == uid and all(
            item.get("summary" if key == "summary" else key, "").casefold() == value.casefold()
            for key, value in changes.items()
        )
    item = _confirmed_item(client, entity_id, matches)
    if item:
        return item
    raise ListOperationError("No se pudo confirmar el cambio; actualiza la lista", 503)


def delete_item(list_id: str, uid: str):
    client, entity_id = _context(list_id, "remove_item")
    before = next((item for item in _items(client, entity_id) if item.get("uid") == uid), None)
    if before is None:
        raise ListOperationError("El ítem ya no está disponible; actualiza la lista", 409)
    try:
        client.todo_action("remove_item", entity_id, item=uid)
    except HomeAssistantError:
        pass
    for attempt in range(3):
        try:
            if not any(item.get("uid") == uid for item in items_for_entity(client, entity_id)):
                return
        except HomeAssistantError:
            pass
        if attempt < 2:
            time.sleep(0.5)
    raise ListOperationError("No se pudo confirmar la eliminación; actualiza la lista", 503)
