"""Server-side OAuth refresh for the selected family Google account."""

import json
import time
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .google import GoogleCalendarError


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class RefreshTokenProvider:
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        if not all((client_id, client_secret, refresh_token)):
            raise ValueError("Google OAuth is not configured")
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token = ""
        self._expires_at = 0.0
        self._lock = Lock()
        self._opener = build_opener(_NoRedirect)

    def __call__(self) -> str:
        with self._lock:
            if self._access_token and time.monotonic() < self._expires_at - 60:
                return self._access_token
            body = urlencode({
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            }).encode()
            request = Request(
                self.TOKEN_URL,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                method="POST",
            )
            try:
                with self._opener.open(request, timeout=15) as response:
                    result = json.load(response)
            except HTTPError as error:
                raise GoogleCalendarError(f"OAuth HTTP {error.code}") from None
            except (URLError, TimeoutError, ValueError):
                raise GoogleCalendarError("Sin conexión") from None
            if not isinstance(result, dict):
                raise GoogleCalendarError("Respuesta OAuth no válida")
            token = result.get("access_token")
            expires_in = result.get("expires_in", 3600)
            if not isinstance(token, str) or not token or not isinstance(expires_in, (int, float)):
                raise GoogleCalendarError("Respuesta OAuth no válida")
            self._access_token = token
            self._expires_at = time.monotonic() + expires_in
            return token
