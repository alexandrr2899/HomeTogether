#!/usr/bin/env python3
"""Bounded Home Together CLI for OpenClaw's internal exec tool."""

import json
import os
import re
import stat
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID


BRIDGE_URL = "http://127.0.0.1:18005/api/v1/jaime/bridge/"
TOKEN_PATH = Path.home() / ".openclaw/hometogether-bridge.token"


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Redirección inesperada")


def arguments(argv):
    if len(argv) not in (3, 4):
        raise ValueError("Indica un turno y una consulta")
    try:
        turn_id = str(UUID(argv[1]))
    except (ValueError, AttributeError):
        raise ValueError("Turno no válido") from None
    action = argv[2]
    value = argv[3] if len(argv) == 4 else None
    if action == "agenda" and value and value.isdecimal() and 1 <= int(value) <= 14:
        return {"turn_id": turn_id, "tool": "consultar_agenda", "arguments": {"dias": int(value)}}
    if action == "lista" and value in {"compras", "super", "tareas"}:
        return {"turn_id": turn_id, "tool": "consultar_lista", "arguments": {"lista": value}}
    if action == "presencia" and value is None:
        return {"turn_id": turn_id, "tool": "consultar_presencia", "arguments": {}}
    if action == "bienestar" and (value is None or re.fullmatch(r"[\w ÁÉÍÓÚÜÑáéíóúüñ.-]{1,80}", value)):
        return {"turn_id": turn_id, "tool": "consultar_bienestar", "arguments": {"persona": value} if value else {}}
    if action in {"proponer-tarea", "proponer-compra"} and value and 1 <= len(value.strip()) <= 255:
        return {"turn_id": turn_id, "tool": "proponer_cambio", "arguments": {
            "tipo": "add_task" if action == "proponer-tarea" else "add_shopping", "nombre": value.strip(),
        }}
    if action == "proponer-completar" and value and 1 <= len(value.strip()) <= 255:
        return {"turn_id": turn_id, "tool": "proponer_cambio", "arguments": {"tipo": "complete_task", "uid": value.strip()}}
    raise ValueError("Consulta no permitida")


def main(argv):
    payload = arguments(argv)
    token_stat = TOKEN_PATH.stat()
    if stat.S_IMODE(token_stat.st_mode) != 0o600 or token_stat.st_uid != os.getuid():
        raise ValueError("Credencial local no disponible")
    token = TOKEN_PATH.read_text().strip()
    if len(token) < 32 or any(char.isspace() for char in token):
        raise ValueError("Credencial local no disponible")
    request = Request(
        BRIDGE_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Forwarded-Proto": "https",
        },
        method="POST",
    )
    try:
        with build_opener(ProxyHandler({}), NoRedirects()).open(request, timeout=25) as response:
            raw = response.read(20_001)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        raise ValueError("Sin conexión o autorización caducada") from None
    if len(raw) > 20_000:
        raise ValueError("Respuesta demasiado grande")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Respuesta no válida") from None
    if not isinstance(result, dict) or not isinstance(result.get("status"), str):
        raise ValueError("Respuesta no válida")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from None
