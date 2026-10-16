"""Bounded OpenClaw turn with Django-owned tools and permissions."""

import json
from uuid import UUID

from .chat_tools import TOOLS, run_tool


class ChatError(Exception):
    pass


SYSTEM_MESSAGE = (
    "Eres Jaime, asistente de Home Together. Responde en español de forma breve. "
    "Consulta las funciones para datos actuales; no inventes eventos, tareas ni presencia. "
    "Una propuesta requiere confirmación posterior del usuario en Home Together. "
    "Nunca afirmes que un cambio externo se guardó al crear una propuesta. "
    "Para consultar o proponer cambios de datos de Home Together usa las funciones proporcionadas. "
    "Conservas tus demás capacidades de OpenClaw bajo sus permisos actuales. No solicites secretos."
)


def run_chat(client, actor, conversation_id: UUID, message: str, bridge_turn=None) -> dict:
    if bridge_turn is not None:
        system = (
            "Eres Jaime, asistente de Home Together. Responde en español de forma breve. "
            "Para consultar datos de Home Together usa la skill hometogether con el turno "
            f"{bridge_turn.pk}. La skill permite consultas y propuestas autorizadas por Django. "
            "Si la consulta falla, dilo sin inventar datos. No uses otras vías para consultar datos familiares. "
            "Para cambios de tareas o compras, la skill solo prepara una propuesta que el usuario debe confirmar en Home Together. "
            "Nunca digas que el cambio externo ya se guardó."
        )
    else:
        system = SYSTEM_MESSAGE
    messages = [{"role": "system", "content": system}, {"role": "user", "content": message}]
    user_key = f"hometogether:{actor.pk}:{conversation_id}"
    proposal_ids = []
    used_ids = set()
    for _ in range(3):
        reply = client.complete(messages, user_key, [] if bridge_turn is not None else TOOLS)
        calls = reply.get("tool_calls")
        if calls and bridge_turn is not None:
            raise ChatError("Jaime solicitó una función fuera del puente autorizado")
        if not calls:
            content = reply.get("content")
            if not isinstance(content, str) or not content.strip() or len(content) > 8000:
                raise ChatError("Jaime no devolvió una respuesta válida")
            return {"status": "Conectado", "message": content.strip(), "proposal_ids": proposal_ids}
        if not isinstance(calls, list) or not 1 <= len(calls) <= 3 or len(used_ids) + len(calls) > 6:
            raise ChatError("Jaime solicitó demasiadas funciones")
        assistant_calls = []
        tool_results = []
        for call in calls:
            if not isinstance(call, dict) or not isinstance(call.get("id"), str) or not isinstance(call.get("function"), dict):
                raise ChatError("Jaime solicitó una función no válida")
            call_id = call["id"]
            function = call["function"]
            name = function.get("name")
            raw = function.get("arguments")
            if not call_id or len(call_id) > 120 or call_id in used_ids or not isinstance(name, str) or not isinstance(raw, str) or len(raw) > 3000:
                raise ChatError("Jaime solicitó una función no válida")
            used_ids.add(call_id)
            try:
                arguments = json.loads(raw)
            except ValueError:
                arguments = None
            if name == "proponer_cambio" and proposal_ids:
                result = {"status": "Rechazado", "detail": "Ya existe una propuesta de este mensaje"}
            else:
                try:
                    result = run_tool(name, arguments, actor)
                except Exception:
                    result = {"status": "Sin conexión", "detail": "No se pudo consultar la fuente"}
            if result.get("proposal_id"):
                proposal_ids.append(result["proposal_id"])
            assistant_calls.append({"id": call_id, "type": "function", "function": {"name": name, "arguments": raw}})
            tool_results.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, ensure_ascii=False, default=str)[:18_000]})
        messages.append({"role": "assistant", "content": reply.get("content") if isinstance(reply.get("content"), str) else "", "tool_calls": assistant_calls})
        messages.extend(tool_results)
    raise ChatError("Jaime no terminó la respuesta")
