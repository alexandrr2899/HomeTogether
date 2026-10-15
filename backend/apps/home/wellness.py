"""Read selected Garmin states for the owner or explicitly allowed viewers."""

from datetime import datetime
from math import isfinite

from django.utils import timezone

from apps.integrations.adapters.home_assistant import HomeAssistantError, configured_home_assistant_client

from .garmin_catalog import GARMIN_STATS, entity_id_for, garmin_prefix
from .models import WellnessPreference


def preferences_for(account):
    preference, _ = WellnessPreference.objects.get_or_create(account=account)
    return preference


def _visible_keys(account, viewer, *, for_jaime=False):
    preference = preferences_for(account)
    selected = preference.visible_metrics if account.pk == viewer.pk else []
    if for_jaime:
        selected = preference.visible_metrics if account.pk == viewer.pk and preference.allow_jaime else []
    elif account.pk != viewer.pk:
        selected = [key for key in preference.visible_metrics if key in preference.shared_metrics]
    return [key for key in selected if key in GARMIN_STATS]


def _safe_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.isoformat() if parsed.tzinfo else None


def available_garmin_stats(account):
    prefix = garmin_prefix(account)
    if not prefix:
        return {"status": "Sin configurar", "stats": []}
    try:
        states = configured_home_assistant_client().get("/api/states")
    except (KeyError, ValueError, HomeAssistantError):
        return {"status": "Sin conexión", "stats": []}
    if not isinstance(states, list):
        return {"status": "Sin conexión", "stats": []}
    by_id = {state.get("entity_id"): state for state in states if isinstance(state, dict)}
    output = []
    for key, definition in GARMIN_STATS.items():
        state = by_id.get(entity_id_for(prefix, key))
        raw = state.get("state") if state else None
        available = raw not in (None, "", "unknown", "unavailable")
        if available and definition.unit is not None:
            available = state.get("attributes", {}).get("unit_of_measurement") == definition.unit
        output.append({"key": key, "label": definition.label, "group": definition.group, "kind": definition.kind, "available": available})
    return {"status": "Conectado", "stats": output}


def _metric_from_state(key, state):
    definition = GARMIN_STATS[key]
    item = {"label": definition.label, "kind": definition.kind, "status": "Sin datos", "value": None,
            "unit": definition.unit, "last_updated": state.get("last_updated")}
    raw = state.get("state")
    if raw in (None, "", "unknown", "unavailable"):
        return item
    if definition.kind == "text":
        if isinstance(raw, str):
            item.update(status="Conectado", value=raw[:180])
            if key == "activity":
                item["started_at"] = _safe_timestamp(state.get("attributes", {}).get("startTime"))
        return item
    if definition.unit is not None and state.get("attributes", {}).get("unit_of_measurement") != definition.unit:
        return item
    try:
        number = float(raw)
        if isfinite(number) and 0 <= number < 10_000_000:
            item.update(status="Conectado", value=round(number, 1))
    except (TypeError, ValueError, OverflowError):
        pass
    return item


def read_wellness(account, viewer, *, for_jaime=False):
    keys = _visible_keys(account, viewer, for_jaime=for_jaime)
    prefix = garmin_prefix(account)
    if not prefix or not keys:
        return {"status": "Sin configurar" if not prefix else "Sin datos", "account_id": account.pk,
                "metrics": {}, "last_checked_at": None}
    try:
        client = configured_home_assistant_client()
    except (KeyError, ValueError):
        return {"status": "Sin configurar", "account_id": account.pk, "metrics": {}, "last_checked_at": None}
    output = {}
    for key in keys:
        definition = GARMIN_STATS[key]
        entity_id = entity_id_for(prefix, key)
        item = {"label": definition.label, "kind": definition.kind, "status": "Sin conexión",
                "value": None, "unit": definition.unit, "last_updated": None}
        try:
            state = client.get(f"/api/states/{entity_id}")
            if isinstance(state, dict) and state.get("entity_id") == entity_id:
                item = _metric_from_state(key, state)
        except HomeAssistantError:
            pass
        output[key] = item
    statuses = {item["status"] for item in output.values()}
    status = "Conectado" if "Conectado" in statuses else "Sin conexión" if "Sin conexión" in statuses else "Sin datos"
    return {"status": status, "account_id": account.pk, "metrics": output,
            "last_checked_at": timezone.now().isoformat()}
