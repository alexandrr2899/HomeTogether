"""Small HTTPS client for Home Assistant; credentials remain on the server."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class HomeAssistantError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class HomeAssistantClient:
    def __init__(self, url: str, token: str, access_client_id: str = "", access_client_secret: str = ""):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Home Assistant requires a plain HTTPS URL")
        if bool(access_client_id) != bool(access_client_secret):
            raise ValueError("Both Cloudflare Access service fields are required together")
        if not token:
            raise ValueError("Home Assistant token is required")
        self.url = url.rstrip("/")
        self.token = token
        self.access_client_id = access_client_id
        self.access_client_secret = access_client_secret
        self._opener = build_opener(_NoRedirect)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "HomeTogether/0.1 (Home Assistant backend)",
        }
        if self.access_client_id:
            headers["CF-Access-Client-Id"] = self.access_client_id
            headers["CF-Access-Client-Secret"] = self.access_client_secret
        return headers

    def _send(self, request: Request):
        try:
            with self._opener.open(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as error:
            raise HomeAssistantError(f"HTTP {error.code}") from None
        except (URLError, TimeoutError, ValueError):
            raise HomeAssistantError("Sin conexión") from None

    def get(self, path: str):
        if not path.startswith("/api/") or "?" in path or "#" in path:
            raise ValueError("Only fixed API paths are accepted")
        request = Request(f"{self.url}{path}", headers=self._headers(), method="GET")
        return self._send(request)

    def todo_items(self, entity_id: str, status: str) -> list[dict]:
        if not entity_id.startswith("todo.") or status not in {"needs_action", "completed"}:
            raise ValueError("Invalid to-do query")
        request = Request(
            f"{self.url}/api/services/todo/get_items?return_response",
            data=json.dumps({"entity_id": entity_id, "status": status}).encode(),
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST",
        )
        result = self._send(request)
        try:
            return result["service_response"][entity_id]["items"]
        except (KeyError, TypeError):
            raise HomeAssistantError("Respuesta de listas no válida") from None

    def todo_action(self, action: str, entity_id: str, **fields) -> None:
        if action not in {"add_item", "update_item", "remove_item"} or not entity_id.startswith("todo."):
            raise ValueError("Acción de lista no válida")
        allowed = {
            "add_item": {"item"},
            "update_item": {"item", "rename", "status"},
            "remove_item": {"item"},
        }[action]
        if not fields or set(fields) - allowed or not fields.get("item"):
            raise ValueError("Campos de lista no válidos")
        request = Request(
            f"{self.url}/api/services/todo/{action}",
            data=json.dumps({"entity_id": entity_id, **fields}).encode(),
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST",
        )
        self._send(request)

    def ping(self) -> bool:
        result = self.get("/api/")
        return isinstance(result, dict) and result.get("message") == "API running."


def configured_home_assistant_client() -> HomeAssistantClient:
    return HomeAssistantClient(
        os.environ["HOME_ASSISTANT_URL"],
        os.environ["HOME_ASSISTANT_TOKEN"],
        os.environ.get("CLOUDFLARE_ACCESS_CLIENT_ID", ""),
        os.environ.get("CLOUDFLARE_ACCESS_CLIENT_SECRET", ""),
    )
