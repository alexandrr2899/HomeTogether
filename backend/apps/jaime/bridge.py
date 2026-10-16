"""OpenClaw bridge for bounded reads and pending proposals."""

import hmac
import os
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from .chat_tools import run_tool
from .models import BridgeTurn


READ_TOOLS = frozenset({"consultar_agenda", "consultar_lista", "consultar_presencia", "consultar_bienestar"})
PROPOSAL_TOOL = "proponer_cambio"
MAX_CALLS_PER_TURN = 6


def token_is_valid(authorization: str) -> bool:
    expected = os.environ.get("HT_JAIME_BRIDGE_TOKEN", "").strip()
    return len(expected) >= 32 and hmac.compare_digest(authorization, f"Bearer {expected}")


def execute_bridge(turn_id: UUID, name: str, arguments: dict) -> tuple[dict, int]:
    if not isinstance(name, str) or name not in READ_TOOLS | {PROPOSAL_TOOL} or not isinstance(arguments, dict):
        return {"status": "Rechazado", "detail": "Operación no permitida"}, 400
    with transaction.atomic():
        turn = BridgeTurn.objects.select_for_update().select_related("actor").filter(pk=turn_id).first()
        if turn is None or turn.expires_at <= timezone.now() or not turn.actor.is_active or not turn.actor.is_staff:
            return {"status": "Rechazado", "detail": "Autorización caducada"}, 403
        if name == PROPOSAL_TOOL and turn.proposal_id:
            return {"status": "Pendiente de confirmación", "proposal_id": str(turn.proposal_id), "kind": turn.proposal.kind}, 200
        if turn.calls >= MAX_CALLS_PER_TURN:
            return {"status": "Rechazado", "detail": "Límite de operaciones alcanzado"}, 429
        turn.calls += 1
        turn.last_tool = name
        if name == PROPOSAL_TOOL:
            try:
                result = run_tool(name, arguments, turn.actor)
            except Exception:
                return {"status": "Sin conexión", "detail": "No se pudo preparar la propuesta"}, 503
            if result.get("proposal_id"):
                turn.proposal_id = result["proposal_id"]
                turn.save(update_fields=["calls", "last_tool", "proposal"])
            else:
                turn.save(update_fields=["calls", "last_tool"])
            return result, 200
        turn.save(update_fields=["calls", "last_tool"])
        actor = turn.actor
    try:
        result = run_tool(name, arguments, actor)
    except Exception:
        return {"status": "Sin conexión", "detail": "No se pudo consultar la fuente"}, 503
    return result, 200
