"""Version shared with the desktop build."""
import os
import re
from pathlib import Path


def _version() -> str:
    configured = os.environ.get("GLACIER_APP_VERSION", "").strip()
    if configured:
        return configured
    module = Path(__file__).resolve()
    for parent in (Path.cwd(), *module.parents):
        try:
            import json
            config = json.loads((parent / "desktop" / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
            version = config.get("version", "")
            if isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
                return version
        except (OSError, ValueError, TypeError):
            continue
    return "0.0.0"


APP_VERSION = _version()
