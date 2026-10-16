"""Small server-side client for OpenClaw's Chat Completions endpoint."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class OpenClawError(Exception):
    pass


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise OpenClawError("OpenClaw devolvió una redirección inesperada")


class OpenClawClient:
    def __init__(self, base_url: str, token: str, agent_id: str):
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise OpenClawError("Dirección de OpenClaw no válida")
        if not token or not agent_id or not agent_id.replace("-", "").replace("_", "").isalnum():
            raise OpenClawError("Configuración de OpenClaw incompleta")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.agent_id = agent_id
        self.opener = build_opener(ProxyHandler({}), _NoRedirects())

    def _request(self, path: str, body: dict | None = None, timeout: int = 30) -> dict:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = Request(
            self.base_url + path, data=data,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json", **({"Content-Type": "application/json"} if data is not None else {})},
            method="POST" if data is not None else "GET",
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(1_000_001)
        except HTTPError as error:
            raise OpenClawError(f"OpenClaw respondió HTTP {error.code}") from None
        except (URLError, TimeoutError, OSError):
            raise OpenClawError("No se pudo conectar con OpenClaw") from None
        if len(raw) > 1_000_000:
            raise OpenClawError("Respuesta de OpenClaw demasiado grande")
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise OpenClawError("OpenClaw devolvió una respuesta no válida") from None
        if not isinstance(result, dict):
            raise OpenClawError("OpenClaw devolvió una respuesta no válida")
        return result

    def probe(self) -> bool:
        models = self._request("/v1/models", timeout=3).get("data")
        return isinstance(models, list) and any(isinstance(item, dict) and item.get("id") == f"openclaw/{self.agent_id}" for item in models)

    def complete(self, messages: list[dict], user_key: str, tools: list[dict]) -> dict:
        result = self._request("/v1/chat/completions", {
            "model": f"openclaw/{self.agent_id}", "user": user_key,
            "stream": False, "messages": messages, "tools": tools, "tool_choice": "auto",
        })
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict) or not isinstance(choices[0].get("message"), dict):
            raise OpenClawError("OpenClaw devolvió una respuesta incompleta")
        return choices[0]["message"]


def configured_client() -> OpenClawClient | None:
    base_url = os.environ.get("HT_OPENCLAW_URL", "").strip()
    token = os.environ.get("HT_OPENCLAW_TOKEN", "").strip()
    if not base_url or not token:
        return None
    return OpenClawClient(base_url, token, os.environ.get("HT_OPENCLAW_AGENT_ID", "main").strip())
