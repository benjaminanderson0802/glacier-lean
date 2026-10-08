"""Read release notes shipped with this version of Glacier."""
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _release_notes_path(version: str) -> Path:
    backend = Path(__file__).resolve().parents[1]
    filename = f"v{version}.md"
    seen = set()
    for parent in (backend.parent.parent, backend.parent, *backend.parents):
        candidate = parent / "docs" / "releases"
        if candidate not in seen:
            seen.add(candidate)
            note = candidate / filename
            if note.is_file():
                return note
    # Keep a stable missing-file path for the 404 response, in both a checkout
    # and the bundled resource layout.
    return backend.parent / "docs" / "releases" / filename


@router.get("/api/releases/current")
def release_notes():
    version = _installed_version()
    if not _VERSION.fullmatch(version):
        raise HTTPException(400, "Enter a valid version number.")
    try:
        markdown = _release_notes_path(version).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(404, "Release notes are not available for this version.") from None
    return {"version": version, "markdown": markdown}


def _installed_version() -> str:
    from desktop_version import _version
    return _version()


@router.get("/api/releases/installed/seen")
def last_seen_version():
    path = Path(os.environ.get("GLACIER_HOME", "data")) / "settings.json"
    try:
        import json
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        saved = {}
    return {"version": saved.get("last_seen_app_version", "")}


@router.put("/api/releases/installed/seen")
def set_last_seen_version(body: dict):
    version = body.get("version") if isinstance(body, dict) else None
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise HTTPException(400, "Enter a valid version number.")
    import json
    path = Path(os.environ.get("GLACIER_HOME", "data")) / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(saved, dict):
            saved = {}
    except (OSError, ValueError, TypeError):
        saved = {}
    saved["last_seen_app_version"] = version
    path.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    return {"version": version}
