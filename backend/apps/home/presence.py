"""Read only the configured person states; never expose tracker coordinates."""

from django.utils import timezone

from apps.integrations.adapters.home_assistant import HomeAssistantError, configured_home_assistant_client
from apps.integrations.models import ExternalEntityLink


def read_presence() -> dict:
    links = list(ExternalEntityLink.objects.select_related("account").filter(
        provider="home_assistant", purpose="presence",
    ).order_by("account__username"))
    if not links:
        return {"status": "Sin configurar", "people": [], "last_checked_at": None}
    people = []
    try:
        client = configured_home_assistant_client()
    except (KeyError, ValueError):
        client = None
    for link in links:
        person = {
            "account_id": link.account_id,
            "username": link.account.get_username(),
            "name": link.account.first_name or link.account.get_username().capitalize(),
            "state": None,
            "label": "Sin configurar" if client is None else "Sin conexión",
            "last_updated": None,
        }
        if client is not None and link.entity_id.startswith("person."):
            try:
                state = client.get(f"/api/states/{link.entity_id}")
                if isinstance(state, dict) and state.get("entity_id") == link.entity_id:
                    raw = state.get("state")
                    if isinstance(raw, str) and raw not in {"unknown", "unavailable", ""}:
                        person["state"] = raw
                        person["label"] = "En casa" if raw == "home" else "Fuera de casa" if raw == "not_home" else raw
                    else:
                        person["label"] = "Sin datos"
                    person["last_updated"] = state.get("last_updated")
            except HomeAssistantError:
                pass
        people.append(person)
    status = "Sin configurar" if client is None else (
        "Conectado" if all(person["label"] not in {"Sin conexión"} for person in people) else "Sin conexión"
    )
    return {"status": status, "people": people, "last_checked_at": timezone.now().isoformat() if client else None}
