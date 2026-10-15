"""Minimal local .env reader; it never evaluates shell syntax."""

import os
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key.startswith(("HT_", "HOME_ASSISTANT_", "CLOUDFLARE_ACCESS_", "GOOGLE_")) and value:
            os.environ.setdefault(key, value)
