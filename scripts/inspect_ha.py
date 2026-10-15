#!/usr/bin/env python3
"""Read-only inventory of a Home Assistant instance. Never prints item contents."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


INTERESTING_DOMAINS = {"calendar", "todo", "person", "device_tracker", "zone"}
INTERESTING_SERVICES = {"calendar", "todo", "shopping_list", "google", "alexa_devices"}
ENTITY_HINTS = ("alexa", "echo", "reminder", "presence")
COMPONENT_HINTS = ("alexa", "apple", "caldav", "google", "hacs", "icloud", "reminder", "shopping", "todo")


def read_env_file(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE lines without shell expansion or execution."""
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key in ("HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN", "CLOUDFLARE_ACCESS_CLIENT_ID", "CLOUDFLARE_ACCESS_CLIENT_SECRET"):
            values[key] = value
    return values


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def get_json(base_url: str, token: str, path: str, access_id: str = "", access_secret: str = ""):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "HomeTogether/0.1 (Home Assistant integration check)",
    }
    if access_id and access_secret:
        headers["CF-Access-Client-Id"] = access_id
        headers["CF-Access-Client-Secret"] = access_secret
    request = Request(
        f"{base_url}{path}",
        headers=headers,
        method="GET",
    )
    try:
        with build_opener(NoRedirect).open(request, timeout=15) as response:
            try:
                return json.load(response)
            except ValueError:
                return {"error": "Respuesta no JSON; posible pantalla de acceso"}
    except HTTPError as error:
        location = error.headers.get("Location", "").lower()
        body = error.read(4096).lower()
        access_hint = ("/cdn-cgi/access" in location or "cloudflareaccess.com" in location
                       or b"cloudflare access" in body)
        return {"error": f"HTTP {error.code}", "cloudflare_access_hint": access_hint}
    except (URLError, TimeoutError, ValueError) as error:
        return {"error": type(error).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Base URL; defaults to HOME_ASSISTANT_URL in .env")
    parser.add_argument("--token-file", type=Path, help="File containing a long-lived access token")
    parser.add_argument("--env-file", type=Path, default=Path(__file__).resolve().parents[1] / ".env")
    args = parser.parse_args()

    local_env = read_env_file(args.env_file)
    base_url = args.url or os.environ.get("HOME_ASSISTANT_URL") or local_env.get("HOME_ASSISTANT_URL", "")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error("Set HOME_ASSISTANT_URL to a plain HTTPS base URL without credentials or query")
    token = args.token_file.read_text().strip() if args.token_file else (
        os.environ.get("HOME_ASSISTANT_TOKEN") or local_env.get("HOME_ASSISTANT_TOKEN", "")
    ).strip()
    if not token:
        parser.error("Set HOME_ASSISTANT_TOKEN in .env or provide --token-file")
    access_id = os.environ.get("CLOUDFLARE_ACCESS_CLIENT_ID") or local_env.get("CLOUDFLARE_ACCESS_CLIENT_ID", "")
    access_secret = os.environ.get("CLOUDFLARE_ACCESS_CLIENT_SECRET") or local_env.get("CLOUDFLARE_ACCESS_CLIENT_SECRET", "")
    if bool(access_id) != bool(access_secret):
        parser.error("Both Cloudflare Access service fields must be set together")
    base_url = base_url.rstrip("/")

    def fetch(path):
        return get_json(base_url, token, path, access_id, access_secret)

    api = fetch("/api/")
    if isinstance(api, dict) and "error" in api:
        print(json.dumps({
            "api": api["error"],
            "cloudflare_access_hint": api.get("cloudflare_access_hint", False),
            "service_headers_sent": bool(access_id),
        }, ensure_ascii=False))
        return 1
    config = fetch("/api/config")
    states = fetch("/api/states")
    services = fetch("/api/services")
    calendars = fetch("/api/calendars")

    entities = []
    if isinstance(states, list):
        for state in states:
            entity_id = state.get("entity_id", "")
            domain = entity_id.partition(".")[0]
            if domain in INTERESTING_DOMAINS or any(hint in entity_id.lower() for hint in ENTITY_HINTS):
                entities.append({
                    "entity_id": entity_id,
                    "supported_features": state.get("attributes", {}).get("supported_features"),
                })

    actions = {}
    if isinstance(services, list):
        for service in services:
            if service.get("domain") in INTERESTING_SERVICES:
                actions[service["domain"]] = sorted(service.get("services", {}).keys())

    calendar_ids = []
    if isinstance(calendars, list):
        calendar_ids = sorted(item.get("entity_id") for item in calendars if item.get("entity_id"))

    components = []
    if isinstance(config, dict) and "error" not in config:
        components = sorted(component for component in config.get("components", [])
                            if any(hint in component.lower() for hint in COMPONENT_HINTS))

    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "api": "available",
        "service_headers_sent": bool(access_id),
        "cloudflare_access": "not determined by a successful API call",
        "version": config.get("version") if isinstance(config, dict) else None,
        "time_zone": config.get("time_zone") if isinstance(config, dict) else None,
        "relevant_components": components,
        "states": "available" if isinstance(states, list) else states.get("error", "unexpected response"),
        "services": "available" if isinstance(services, list) else services.get("error", "unexpected response"),
        "calendars": "available" if isinstance(calendars, list) else calendars.get("error", "unexpected response"),
        "calendar_entity_ids": calendar_ids,
        "candidate_entities": sorted(entities, key=lambda item: item["entity_id"]),
        "available_action_names": actions,
        "note": "Read-only snapshot. It does not prove an action works or identify the data source or propagation path.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not isinstance(states, list) or not isinstance(services, list):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
