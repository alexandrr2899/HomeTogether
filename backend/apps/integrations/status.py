"""Configuration status only; live health requires actual provider checks."""

import os
from urllib.parse import urlsplit, urlunsplit


def google_calendar_status() -> str:
    configured = all(os.environ.get(name) for name in (
        "HT_GOOGLE_CALENDAR_ID", "HT_GOOGLE_CLIENT_ID", "HT_GOOGLE_CLIENT_SECRET", "HT_GOOGLE_REFRESH_TOKEN",
    ))
    return "Pendiente de verificación" if configured else "Sin configurar"


def home_assistant_status() -> str:
    configured = bool(os.environ.get("HOME_ASSISTANT_URL") and os.environ.get("HOME_ASSISTANT_TOKEN"))
    return "Pendiente de verificación" if configured else "Sin configurar"


def home_assistant_web_url() -> str | None:
    """Expose only a clean HTTPS origin for a separate browser session."""
    try:
        address = urlsplit(os.environ.get("HOME_ASSISTANT_URL", ""))
        port = address.port
        if (address.scheme != "https" or not address.hostname or address.username or
                address.password or address.query or address.fragment):
            return None
        if port is not None and not 1 <= port <= 65535:
            return None
        return urlunsplit(("https", address.netloc, "/", "", ""))
    except ValueError:
        return None
