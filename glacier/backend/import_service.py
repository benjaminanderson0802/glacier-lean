"""Import local ChatGPT and Claude export files into the searchable memory vault."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

import vault
import secrets_store

# Import the parser package, which lives beside backend/ rather than inside it.
_IMPORTER_ROOT = Path(__file__).resolve().parents[2]
if str(_IMPORTER_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_IMPORTER_ROOT))
from glacier.importers import chatgpt, claude

MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_FILES = 10_000
_SOURCES = {"chatgpt": chatgpt, "claude": claude}


def _home() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")).resolve()


def _state_path() -> Path:
    return _home() / "import_sources.json"


def _state() -> dict:
    try:
        state = json.loads(_state_path().read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".imports-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _copy_upload(source, filename: str) -> Path:
    folder = _home() / "import_sources"
    folder.mkdir(parents=True, exist_ok=True)
    name = Path(filename or "export.zip").name
    if not name or name in {".", ".."}:
        name = "export.zip"
    suffix = Path(name).suffix.lower()
    if suffix not in {".zip", ".json"}:
        raise ValueError("Choose a ChatGPT or Claude export ZIP or JSON file")
    fd, temp = tempfile.mkstemp(dir=folder, prefix=".upload-")
    total = 0
    try:
        with os.fdopen(fd, "wb") as target:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 1024 * 1024 * 1024:
                    raise ValueError("This export file is too large")
                target.write(chunk)
        destination = folder / name
        if destination.exists():
            destination = folder / f"{Path(name).stem}-{hashlib.sha256(Path(temp).read_bytes()).hexdigest()[:12]}{suffix}"
        os.replace(temp, destination)
        return destination
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _json_bytes(path: Path) -> bytes:
    if not zipfile.is_zipfile(path):
        size = path.stat().st_size
        if size > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("This export is too large to import")
        return path.read_bytes()
    try:
        with zipfile.ZipFile(path) as archive:
            entries = [item for item in archive.infolist() if not item.is_dir()]
            if len(entries) > MAX_ARCHIVE_FILES:
                raise ValueError("This export contains too many files")
            if sum(item.file_size for item in entries) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("This export is too large to import")
            candidates = [item for item in entries if Path(item.filename).name.casefold() == "conversations.json"]
            if not candidates:
                candidates = [item for item in entries if Path(item.filename).suffix.casefold() == ".json"]
            if not candidates:
                raise ValueError("The ZIP does not contain a conversations JSON file")
            selected = max(candidates, key=lambda item: (item.file_size, item.filename))
            with archive.open(selected) as stream:
                chunks, total = [], 0
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_UNCOMPRESSED_BYTES:
                        raise ValueError("This export is too large to import")
                    chunks.append(chunk)
            return b"".join(chunks)
    except zipfile.BadZipFile as exc:
        raise ValueError("This export ZIP is damaged") from exc


def _existing_notes(source: str) -> dict[str, tuple[str, str]]:
    result = {}
    for path in vault.list_notes(".md", f"imports/{source}"):
        try:
            body = vault.read_raw_note(path)
        except (OSError, ValueError):
            continue
        source_id = _field(body, "source_id")
        digest = _field(body, "content_hash")
        if source_id:
            result[source_id] = (path, digest)
    return result


def _field(body: str, field: str) -> str:
    import re
    match = re.search(rf"(?m)^{field}:\s*(.*?)\s*$", body)
    return match.group(1).strip('"') if match else ""


def _process(source: str, path: Path) -> dict[str, int]:
    raw = _json_bytes(path)
    try:
        notes = _SOURCES[source].parse(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"This does not look like a valid {source.title()} export") from exc
    known = _existing_notes(source)
    counts = {"added": 0, "updated": 0, "unchanged": 0}
    seen_ids = set()
    for note in notes:
        source_id = note.source_id
        if not source_id:
            continue
        if source_id in seen_ids:
            continue
        seen_ids.add(source_id)
        # Redact before hashing and storage so deduplication reflects saved content.
        safe_body = secrets_store.redact(note.body)
        content = safe_body.split("\n\n", 1)[1] if "\n\n" in safe_body else ""
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        prior = known.get(source_id)
        if prior and prior[1] == digest:
            counts["unchanged"] += 1
            continue
        path_to_write = prior[0] if prior else note.path
        if not prior:
            existing_path = next((item for item in vault.list_notes(".md", f"imports/{source}")
                                  if item == path_to_write), None)
            if existing_path:
                suffix = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:8]
                path_to_write = f"{Path(note.path).with_suffix('').as_posix()}-{suffix}.md"
        custom = safe_body.split("\n", 1)
        if custom[0] == "---":
            title = _field(safe_body, "title").replace('"', "'")
            safe_body = safe_body.replace("\n---", f"\ncontent_hash: {digest}\n---", 1)
            if title:
                safe_body = safe_body.replace("\n\n## ", f"\n\n# {title}\n\n## ", 1)
        else:
            safe_body = f"---\ncontent_hash: {digest}\n---\n\n{safe_body}"
        vault.write_note(path_to_write, safe_body, author="glacier-import")
        counts["updated" if prior else "added"] += 1
    return counts


def import_export(source: str, path: str | os.PathLike | None = None, *, upload=None, filename: str = "") -> dict[str, int]:
    if source not in _SOURCES:
        raise ValueError("Choose ChatGPT or Claude as the export source")
    if (path is None) == (upload is None):
        raise ValueError("Choose one export file to import")
    if upload is not None:
        export_path = _copy_upload(upload, filename)
    else:
        export_path = Path(path).expanduser().resolve()
        if not export_path.is_file():
            raise ValueError("The export file could not be found")
        if export_path.suffix.lower() not in {".zip", ".json"}:
            raise ValueError("Choose a ChatGPT or Claude export ZIP or JSON file")
    counts = _process(source, export_path)
    state = _state()
    state[source] = {"path": str(export_path), "last_import": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), **counts}
    _save_state(state)
    return counts


def _watched_newest() -> Path | None:
    folder = os.environ.get("GLACIER_IMPORT_DIR", "")
    if not folder or not Path(folder).is_dir():
        return None
    files = [p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in {".zip", ".json"}]
    return max(files, key=lambda p: (p.stat().st_mtime_ns, p.name)) if files else None


def _source_in(path: Path) -> str | None:
    try:
        raw = _json_bytes(path)
    except ValueError:
        raise
    except OSError:
        return None
    try:
        data = json.loads(raw.decode("utf-8-sig"))
        first = data[0] if isinstance(data, list) and data else {}
        if isinstance(first, dict):
            if "mapping" in first or "id" in first:
                return "chatgpt"
            if "uuid" in first or "chat_messages" in first:
                return "claude"
    except (ValueError, UnicodeDecodeError):
        pass
    return None


def refresh() -> dict[str, dict[str, int]]:
    state = _state()
    watched = _watched_newest()
    results = {}
    if watched:
        source = _source_in(watched)
        if source:
            results[source] = import_export(source, watched)
    else:
        for source, saved in list(state.items()):
            saved_path = Path(saved.get("path", ""))
            if saved_path.is_file() and source in _SOURCES:
                results[source] = import_export(source, saved_path)
    return results


def list_imports() -> list[dict]:
    state = _state()
    return [{"source": source, "last_import": value.get("last_import"),
             "added": value.get("added", 0), "updated": value.get("updated", 0),
             "unchanged": value.get("unchanged", 0)}
            for source, value in sorted(state.items()) if source in _SOURCES]
