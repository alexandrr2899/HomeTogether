"""Google authorization-code flow for the family calendar connection."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings


SCOPES = (
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events",
)
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class OAuthSetupError(Exception):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def redirect_uri() -> str:
    uri = settings.GOOGLE_REDIRECT_URI
    parsed = urlsplit(uri)
    local_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    if (not (local_http or parsed.scheme == "https") or not parsed.netloc or
            parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise OAuthSetupError("URI de redirección no válida")
    if parsed.path != "/api/v1/calendar/oauth/callback/":
        raise OAuthSetupError("Ruta de redirección no válida")
    return uri


def authorization_url(state: str) -> str:
    client_id = os.environ.get("HT_GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("HT_GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise OAuthSetupError("Cliente de Google sin configurar")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str, opener=None) -> str:
    client_id = os.environ.get("HT_GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("HT_GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret or not code:
        raise OAuthSetupError("Cliente de Google sin configurar")
    body = urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
    }).encode()
    request = Request(
        TOKEN_URL,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with (opener or build_opener(_NoRedirect)).open(request, timeout=15) as response:
            result = json.load(response)
    except HTTPError as error:
        raise OAuthSetupError(f"Google rechazó el intercambio (HTTP {error.code})") from None
    except (URLError, TimeoutError, ValueError):
        raise OAuthSetupError("No se pudo completar la conexión con Google") from None
    if not isinstance(result, dict):
        raise OAuthSetupError("Respuesta OAuth no válida")
    granted = set(result.get("scope", "").split())
    if not set(SCOPES).issubset(granted):
        raise OAuthSetupError("Google no concedió los permisos necesarios")
    refresh_token = result.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise OAuthSetupError("Google no entregó un token de renovación; repite el consentimiento")
    return refresh_token
