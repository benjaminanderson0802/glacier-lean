"""Local original files and searchable document notes."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import io
from pathlib import Path

from markitdown import MarkItDown

import vault


DEFAULT_PROJECT = "Inbox"
_BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi"}
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _home() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")).resolve()


def _valid_name(name: str) -> bool:
    return (bool(name) and name not in {".", ".."} and name == name.strip()
            and not name.endswith(".") and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _().-]{0,180}", name))
            and name.split(".", 1)[0].upper() not in _WINDOWS_RESERVED)


def validate_project(name: str) -> str:
    if not _valid_name(name):
        raise ValueError("Use a project name with plain letters, numbers, spaces, hyphens, or underscores")
    return name


def validate_filename(name: str) -> str:
    # Multipart filenames must be a single safe filename, not a path supplied by the client.
    if not _valid_name(name) or "/" in name or "\\" in name or ":" in name:
        raise ValueError("That file name is not allowed")
    if Path(name).suffix.lower() in _BLOCKED_EXTENSIONS:
        raise PermissionError("This file type is not allowed")
    return name


def max_upload_bytes() -> int:
    try:
        mb = float(os.environ.get("GLACIER_MAX_UPLOAD_MB", "50"))
    except ValueError:
        mb = 50
    return max(1, int(max(0, mb) * 1024 * 1024))


def _entries(project: str | None = None) -> list[dict]:
    root = _home() / "files"
    if not root.is_dir():
        return []
    entries = []
    projects = [root / project] if project else sorted(p for p in root.iterdir() if p.is_dir())
    for folder in projects:
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.name != ".gitkeep":
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                entries.append(_entry(path, folder.name, digest))
    return entries


def _entry(path: Path, project: str, digest: str, duplicate: bool = False) -> dict:
    note = f"files/{project}/{path.name}.md"
    return {"name": path.name, "project": project, "size": path.stat().st_size,
            "sha256": digest, "path": str(path.relative_to(_home())).replace(os.sep, "/"),
            "note": note if (_home() / "vault" / note).is_file() else None, "duplicate": duplicate}


def list_files(project: str | None = None) -> list[dict]:
    if project:
        validate_project(project)
    return _entries(project)


def list_projects() -> list[dict]:
    root = _home() / "files"
    names = {DEFAULT_PROJECT}
    if root.is_dir():
        names.update(p.name for p in root.iterdir() if p.is_dir())
    return [{"name": name, "count": len(_entries(name))} for name in sorted(names, key=str.casefold)]


def create_project(name: str) -> dict:
    name = validate_project(name)
    (_home() / "files" / name).mkdir(parents=True, exist_ok=True)
    return {"name": name, "count": 0}


def save_upload(filename: str, project: str | None, content: bytes) -> dict:
    filename = validate_filename(filename)
    project = validate_project(project or DEFAULT_PROJECT)
    digest = hashlib.sha256(content).hexdigest()
    folder = _home() / "files" / project
    folder.mkdir(parents=True, exist_ok=True)
    for existing in sorted(folder.iterdir()):
        if existing.is_file() and hashlib.sha256(existing.read_bytes()).hexdigest() == digest:
            return _entry(existing, project, digest, duplicate=True)

    destination = folder / filename
    if destination.exists():
        stem, suffix = destination.stem, destination.suffix
        index = 2
        while (folder / f"{stem} ({index}){suffix}").exists():
            index += 1
        destination = folder / f"{stem} ({index}){suffix}"
    fd, temp_name = tempfile.mkstemp(dir=folder)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    note_path = f"files/{project}/{destination.name}.md"
    try:
        converted = MarkItDown().convert_stream(io.BytesIO(content), file_extension=destination.suffix or None)
        text = (converted.text_content or "").strip()
        if text:
            relative_original = os.path.relpath(destination, Path(vault.VAULT) / "files" / project).replace(os.sep, "/")
            vault.write_note(note_path, f"# {destination.name}\n\n[Download original]({relative_original})\n\n{text}\n", author="owner")
    except Exception:
        # Some file types are valid originals but aren't readable by MarkItDown.
        pass
    return _entry(destination, project, digest)
