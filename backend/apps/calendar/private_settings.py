"""Persist local Google OAuth settings outside Git without printing values."""

import os
import stat
import tempfile
from pathlib import Path

from django.conf import settings


ALLOWED_KEYS = {"HT_GOOGLE_REFRESH_TOKEN", "HT_GOOGLE_CALENDAR_ID"}


class PrivateSettingsError(Exception):
    pass


def save_private_setting(key: str, value: str, path: Path | None = None) -> None:
    if key not in ALLOWED_KEYS or not isinstance(value, str) or not value or "\n" in value or "\r" in value:
        raise PrivateSettingsError("Configuración privada no válida")
    target = path or settings.BASE_DIR.parent / ".env"
    if target.is_symlink():
        raise PrivateSettingsError("El archivo privado no puede ser un enlace")
    try:
        if target.exists():
            info = target.stat()
            if not stat.S_ISREG(info.st_mode):
                raise PrivateSettingsError("El archivo privado no es regular")
            original = target.read_text()
        else:
            original = ""
        lines = original.splitlines()
        replacement = f"{key}={value}"
        output = []
        found = False
        for line in lines:
            if line.split("=", 1)[0].strip() == key and "=" in line and not line.lstrip().startswith("#"):
                if not found:
                    output.append(replacement)
                    found = True
            else:
                output.append(line)
        if not found:
            output.append(replacement)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".env.", dir=target.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write("\n".join(output) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError:
        raise PrivateSettingsError("No se pudo guardar la configuración privada") from None
    os.environ[key] = value
