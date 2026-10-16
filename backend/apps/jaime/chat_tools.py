"""Only Django executes these user-scoped tools; OpenClaw supplies arguments."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.calendar.adapters.google import GoogleCalendarError
from apps.calendar.service import calendar_reader
from apps.home.presence import read_presence
from apps.home.wellness import read_wellness
from apps.lists.service import read_lists

from .serializers import ActionProposalSerializer


TOOLS = [
    {"type": "function", "function": {"name": "consultar_agenda", "description": "Consulta los próximos eventos del calendario familiar, como máximo 14 días.", "parameters": {"type": "object", "properties": {"dias": {"type": "integer", "minimum": 1, "maximum": 14}}, "required": ["dias"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "consultar_lista", "description": "Consulta ítems de una lista existente de Home Assistant y Alexa.", "parameters": {"type": "object", "properties": {"lista": {"type": "string", "enum": ["tareas", "compras", "super"]}}, "required": ["lista"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "consultar_presencia", "description": "Consulta la presencia de Alexander y Lastenia en Home Assistant.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "consultar_bienestar", "description": "Consulta indicadores Garmin autorizados expresamente para Jaime. Si el usuario nombra a otra persona, indica su nombre en persona.", "parameters": {"type": "object", "properties": {"persona": {"type": "string", "maxLength": 80}}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "proponer_cambio", "description": "Prepara un cambio para revisión en Home Together. No ejecuta la acción externa.", "parameters": {"type": "object", "properties": {"tipo": {"type": "string", "enum": ["add_task", "add_shopping", "complete_task"]}, "nombre": {"type": "string"}, "uid": {"type": "string"}}, "required": ["tipo"], "additionalProperties": False}}},
]


def run_tool(name: str, arguments: dict, actor) -> dict:
    if not isinstance(arguments, dict):
        return {"status": "Rechazado", "detail": "Argumentos no válidos"}
    if name == "consultar_agenda":
        days = arguments.get("dias")
        if set(arguments) != {"dias"} or type(days) is not int or not 1 <= days <= 14:
            return {"status": "Rechazado", "detail": "Indica entre 1 y 14 días"}
        reader = calendar_reader()
        if reader is None:
            return {"status": "Sin configurar", "source": "google_calendar", "events": []}
        try:
            result = reader.events(timezone.now(), timezone.now() + timedelta(days=days))
        except GoogleCalendarError:
            return {"status": "Sin conexión", "source": "google_calendar", "events": []}
        events = result.get("events", [])
        return {"status": "Conectado", "source": "google_calendar", "events": [{key: event.get(key) for key in ("id", "summary", "start", "end", "location", "status") if key in event} for event in events[:30]], "more": len(events) > 30 or bool(result.get("next_page_token")), "checked_at": timezone.now().isoformat()}
    if name == "consultar_lista":
        list_id = arguments.get("lista")
        if set(arguments) != {"lista"} or list_id not in {"tareas", "compras", "super"}:
            return {"status": "Rechazado", "detail": "Lista no permitida"}
        item = next((entry for entry in read_lists() if entry["id"] == list_id), None)
        if item is None:
            return {"status": "Sin configurar", "items": []}
        items = item["items"]
        return {"status": item["status"], "source": "home_assistant", "list": item["name"], "items": items[:40], "more": len(items) > 40, "checked_at": timezone.now().isoformat()}
    if name == "consultar_presencia":
        if arguments:
            return {"status": "Rechazado", "detail": "Argumentos no permitidos"}
        result = read_presence()
        return {"status": result["status"], "source": "home_assistant", "people": [{"name": person["name"], "label": person["label"], "last_updated": person["last_updated"]} for person in result["people"]], "checked_at": result["last_checked_at"]}
    if name == "consultar_bienestar":
        person = arguments.get("persona")
        if set(arguments) - {"persona"} or (person is not None and (not isinstance(person, str) or not 1 <= len(person.strip()) <= 80)):
            return {"status": "Rechazado", "detail": "Argumentos no permitidos"}
        account = actor
        if person and person.strip().casefold() not in {"yo", "mí", "mi", "propio"}:
            matches = list(get_user_model().objects.filter(is_staff=True, is_active=True).filter(
                Q(username__iexact=person.strip()) | Q(first_name__iexact=person.strip()))[:2])
            if len(matches) != 1:
                return {"status": "Rechazado", "detail": "Persona no disponible"}
            account = matches[0]
        result = read_wellness(account, actor, for_jaime=True)
        return {"status": result["status"], "source": "garmin_via_home_assistant", "person": account.first_name or account.get_username(), "metrics": result["metrics"], "checked_at": result["last_checked_at"]}
    if name == "proponer_cambio":
        kind = arguments.get("tipo")
        if kind in {"add_task", "add_shopping"} and set(arguments) == {"tipo", "nombre"}:
            payload = {"summary": arguments["nombre"]}
        elif kind == "complete_task" and set(arguments) == {"tipo", "uid"}:
            payload = {"uid": arguments["uid"]}
        else:
            return {"status": "Rechazado", "detail": "Cambio no permitido"}
        serializer = ActionProposalSerializer(data={"kind": kind, "payload": payload})
        if not serializer.is_valid():
            return {"status": "Rechazado", "detail": "Datos de la propuesta no válidos"}
        proposal = serializer.save(actor=actor)
        return {"status": "Pendiente de confirmación", "proposal_id": str(proposal.id), "kind": proposal.kind}
    return {"status": "Rechazado", "detail": "Función no permitida"}
