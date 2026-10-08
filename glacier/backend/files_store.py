"""Local original files and searchable document notes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import vault
import ocr
from app_paths import app_data_home

DEFAULT_PROJECT = "Inbox"
_BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".msi", ".com", ".scr", ".vbs", ".js", ".jse", ".wsf", ".hta", ".msc", ".cpl", ".dll", ".lnk", ".reg", ".jar", ".psm1", ".appimage"}
_MAGIC = (b"MZ", b"\x7fELF", b"#!", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe")
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_MAX_TEXT_BYTES = 2 * 1024 * 1024
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
_TESSERACT_URL = "https://github.com/tesseract-ocr/tesseract"
_project_locks: dict[str, threading.Lock] = {}
_project_locks_guard = threading.Lock()


def _project_lock(folder: Path) -> threading.Lock:
    key = str(folder.resolve())
    with _project_locks_guard:
        return _project_locks.setdefault(key, threading.Lock())


def _home() -> Path:
    return app_data_home()


def _valid_name(name: str) -> bool:
    return (bool(name) and name not in {".", ".."} and name == name.strip() and not name.endswith(".")
            and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _().-]{0,180}", name))
            and name.split(".", 1)[0].upper() not in _WINDOWS_RESERVED)


def validate_project(name: str) -> str:
    if not _valid_name(name):
        raise ValueError("Use a project name with plain letters, numbers, spaces, hyphens, or underscores")
    return name


def validate_filename(name: str) -> str:
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


def too_large_message() -> str:
    return f"This file is too large. The upload limit is {os.environ.get('GLACIER_MAX_UPLOAD_MB', '50')} MB."


def _index_path(folder: Path) -> Path:
    return folder / ".index.json"


def _load_index(folder: Path) -> dict[str, dict]:
    try:
        value = json.loads(_index_path(folder).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_index(folder: Path, index: dict[str, dict]) -> None:
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".index-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(index, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, _index_path(folder))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _entry(path: Path, project: str, digest: str, duplicate: bool = False, message: str | None = None) -> dict:
    note = f"files/{project}/{path.name}.md"
    row = {"name": path.name, "project": project, "size": path.stat().st_size,
           "sha256": digest, "path": str(path.relative_to(_home())).replace(os.sep, "/"),
           "note": note if (_home() / "vault" / note).is_file() else None, "duplicate": duplicate}
    if message:
        row["message"] = message
    return row


def _entries(project: str | None = None) -> list[dict]:
    root = _home() / "files"
    if not root.is_dir():
        return []
    projects = [root / project] if project else sorted(p for p in root.iterdir() if p.is_dir())
    entries = []
    for folder in projects:
        if not folder.is_dir():
            continue
        index = _load_index(folder)
        for name, metadata in sorted(index.items()):
            path = folder / name
            if path.is_file() and isinstance(metadata, dict):
                entries.append(_entry(path, folder.name, str(metadata.get("sha256", ""))))
    return entries


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


def _check_magic(path: Path) -> None:
    with path.open("rb") as stream:
        start = stream.read(8)
    if any(start.startswith(prefix) for prefix in _MAGIC):
        raise PermissionError("This file type is not allowed")


def _convert_in_child(path: Path) -> str:
    script = (
        "import sys\n"
        "try:\n"
        "    import resource\n"
        "    cap = 2 * 1024 * 1024 * 1024\n"
        "    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))\n"
        "except ImportError:\n"
        "    pass\n"
        "from markitdown import MarkItDown\n"
        "r = MarkItDown().convert(sys.argv[1])\n"
        "sys.stdout.buffer.write((r.text_content or '').encode('utf-8')[:2097152])\n"
    )
    # The address-space cap guards against hostile documents. The file-type detector (onnxruntime) starts one
    # thread per CPU core and glibc reserves a malloc arena per thread, so on 16+ thread machines the default
    # arenas alone exceed a tight cap (measured: 1 GB cap succeeded 1 in 5 times on a 16-thread laptop).
    # Two arenas keep the reservation small and well under the cap.
    env = dict(os.environ, MALLOC_ARENA_MAX="2")
    result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True,
                            timeout=60, check=False, env=env)
    if result.returncode:
        raise RuntimeError("document conversion failed")
    return result.stdout[:_MAX_TEXT_BYTES].decode("utf-8", errors="replace")


def save_upload(filename: str, project: str | None, source) -> dict:
    """Copy UploadFile.file to disk in bounded chunks while calculating its digest."""
    filename = validate_filename(filename)
    project = validate_project(project or DEFAULT_PROJECT)
    folder = _home() / "files" / project
    folder.mkdir(parents=True, exist_ok=True)
    with _project_lock(folder):
        index = _load_index(folder)
        fd, tmp_name = tempfile.mkstemp(dir=folder, prefix=".upload-")
        digest = hashlib.sha256()
        size = 0
        try:
            with os.fdopen(fd, "wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_upload_bytes():
                        raise OverflowError
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            staged = Path(tmp_name)
            _check_magic(staged)
            hexdigest = digest.hexdigest()
            for name, metadata in index.items():
                if metadata.get("sha256") == hexdigest and (folder / name).is_file():
                    staged.unlink()
                    return _entry(folder / name, project, hexdigest, duplicate=True)
            stem, suffix = Path(filename).stem, Path(filename).suffix
            candidate = filename
            number = 2
            while True:
                destination = folder / candidate
                try:
                    os.link(staged, destination)
                    break
                except FileExistsError:
                    candidate = f"{stem} ({number}){suffix}"
                    number += 1
            staged.unlink()
            index[candidate] = {"sha256": hexdigest, "size": size}
            _write_index(folder, index)
        except OverflowError as exc:
            raise ValueError(too_large_message()) from exc
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    message = None
    note_path = f"files/{project}/{destination.name}.md"
    if destination.suffix.lower() in _IMAGE_EXTENSIONS:
        # Images: offline OCR (Tesseract, if installed) in a capped child process; the note is always written so
        # the image can be found by name, with the recognised text or a plain hint on how to get it.
        try:
            ocr_text, ocr_error = ocr.recognize(destination)
        except Exception:
            ocr_text, ocr_error = "", "ocr_failed"
        text = "" if ocr_error else ocr_text.strip()
        hint = ""
        if ocr_error == "decompression_bomb":
            message = "This image is too large to read safely. The original file was saved."
        elif not ocr.find_tesseract():
            hint = f"Text in images can be made searchable by installing Tesseract (free and open source): {_TESSERACT_URL}"
            message = f"File saved. {hint}"
        elif not text:
            message = "File saved. No text was found in the image."
        section = f"## Text found in the image\n\n{text}" if text else hint
        try:
            vault.write_note(note_path, f"# {destination.name}\n\n[Download original](../../../files/{project}/{destination.name})\n\n{section}\n", author="owner")
        except Exception:
            message = "File saved, but its searchable note could not be saved."
        return _entry(destination, project, hexdigest, message=message)
    message = None
    note_path = f"files/{project}/{destination.name}.md"
    try:
        text = _convert_in_child(destination).strip()
    except Exception:
        text = ""
    if not text:
        message = "File saved, but its text couldn't be read."
    else:
        try:
            vault.write_note(note_path, f"# {destination.name}\n\n[Download original](../../../files/{project}/{destination.name})\n\n{text}\n", author="owner")
        except Exception:
            message = "File saved, but its text couldn't be read because its searchable note could not be saved."
    return _entry(destination, project, hexdigest, message=message)
