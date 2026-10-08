"""Atomic, link-aware note renames for the memory vault."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import PurePosixPath

import git

import memory_meta
import memory_links
import vault


FROM_TRAILER = "Glacier-Rename-From: "
TO_TRAILER = "Glacier-Rename-To: "
_WINDOWS_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_DEVICE = re.compile(r"^(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?$", re.I)


def _check_name(path: str) -> str:
    if not isinstance(path, str) or not path or path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path):
        raise ValueError("That note path is not allowed")
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("That note path is not allowed")
    for part in parts:
        stem = part.split(".", 1)[0]
        if (_WINDOWS_INVALID.search(part) or part.endswith((".", " ")) or
                any(ord(char) < 32 for char in part) or _DEVICE.fullmatch(part) or
                any(char in part for char in "#^[]")):
            raise ValueError("That note name is not allowed")
    if not normalized.lower().endswith(".md"):
        raise ValueError("Memory notes must be Markdown files")
    return normalized


def _protected(path: str) -> None:
    folded = path.casefold().lstrip("./")
    if folded == "claims" or folded.startswith("claims/"):
        raise ValueError("Claims can't be renamed from memory")
    if folded == "runs" or folded.startswith("runs/"):
        raise ValueError("Run notes can't be renamed from memory")


def _full(path: str) -> str:
    full = vault.safe_path(path)
    relative = os.path.relpath(full, vault.VAULT).replace(os.sep, "/")
    if relative.casefold() != path.casefold():
        # Reject symlink aliases and paths that resolve through a different vault entry.
        raise ValueError("That note path is not allowed")
    return full


def _rewrite_body(body: str, source: str, old_path: str, new_path: str,
                  resolver: memory_links.LinkResolver) -> tuple[str, bool]:
    """Rewrite only references that the reader/map resolve to the moved note."""
    masked = memory_links._without_code(body)
    edits: list[tuple[int, int, str]] = []
    for pattern in (memory_links._WIKI, memory_links._MARKDOWN):
        for match in pattern.finditer(masked):
            raw = match.group(1) if pattern is memory_links._WIKI else match.group(2).strip("<>")
            target, suffix = "", ""
            if pattern is memory_links._WIKI:
                before_alias = raw.split("|", 1)[0].strip()
                target = before_alias.split("#", 1)[0].strip()
                suffix = before_alias[len(target):]
            else:
                from urllib.parse import unquote, urlsplit
                parsed = urlsplit(raw)
                if parsed.scheme or parsed.netloc or raw.startswith("//"):
                    continue
                target = unquote(parsed.path)
                suffix = raw[len(parsed.path):]
            canonical, status = resolver.resolve(target, source)
            if status != "resolved" or not canonical or canonical.casefold() != old_path.removesuffix(".md").casefold():
                continue
            new_target = new_path.removesuffix(".md")
            if pattern is memory_links._WIKI:
                alias = raw.split("|", 1)[1] if "|" in raw else None
                replacement = new_target + suffix + ("|" + alias if alias is not None else "")
                edits.append((match.start(1), match.end(1), replacement))
            else:
                encoded = new_target + ".md"
                # Preserve a relative Markdown link when the original was relative.
                if target.startswith(("./", "../")):
                    import posixpath
                    source_dir = source.rsplit("/", 1)[0] if "/" in source else ""
                    encoded = posixpath.relpath(new_target + ".md", source_dir or ".")
                    if not encoded.startswith("."):
                        encoded = "./" + encoded
                replacement = encoded + suffix
                start, end = match.span(2)
                original = body[start:end]
                if original.startswith("<") and original.endswith(">"):
                    replacement = "<" + replacement + ">"
                edits.append((start, end, replacement))
    rewritten = body
    for start, end, value in sorted(edits, reverse=True):
        rewritten = rewritten[:start] + value + rewritten[end:]
    return rewritten, bool(edits)


def rename(source: str, target: str) -> dict:
    old = _check_name(source)
    new = _check_name(target)
    _protected(old)
    _protected(new)
    old_full, new_full = _full(old), _full(new)
    events = []
    with vault._lock:
        if not os.path.isfile(old_full):
            raise FileNotFoundError("That note could not be found")
        if os.path.exists(new_full) or os.path.normcase(old_full) == os.path.normcase(new_full):
            raise FileExistsError("A note already exists at that path")

        paths = vault.list_notes(".md")
        notes = []
        for path in paths:
            try:
                text = vault.read_raw_note(path)
            except (OSError, ValueError):
                continue
            _, body = memory_meta.parse(text, path)
            notes.append((path, text, body))
        resolver = memory_links.LinkResolver([p.removesuffix(".md") for p, _, _ in notes])
        rewrites = {}
        for path, text, body in notes:
            if path.casefold() == old.casefold():
                continue
            changed_body, changed = _rewrite_body(body, path.removesuffix(".md"), old, new, resolver)
            if changed:
                match = re.match(r"\A---\s*\n.*?\n---\s*\n?", text, re.S)
                prefix = match.group(0) if match else ""
                rewrites[path] = prefix + changed_body

        old_text = vault.read_raw_note(old)
        original_old_text = old_text
        old_meta, old_body = memory_meta.parse(old_text, old)
        old_stem = os.path.splitext(os.path.basename(old))[0]
        new_title = os.path.splitext(os.path.basename(new))[0]
        title = old_meta["title"]
        # Change title only when it was inferred from the old filename.
        if title == old_stem:
            meta_match = re.search(r'(?m)^title:\s*(.*)$', old_text)
            if meta_match:
                old_text = old_text[:meta_match.start(1)] + json.dumps(new_title, ensure_ascii=False) + old_text[meta_match.end(1):]
            old_text = re.sub(r"(?m)^(#\s+)" + re.escape(old_stem) + r"(\s*#*\s*)$",
                              lambda match: match.group(1) + new_title + match.group(2), old_text, count=1)

        os.makedirs(os.path.dirname(new_full), exist_ok=True)
        os.replace(old_full, new_full)
        updated = []
        try:
            for path, text in rewrites.items():
                full = vault.safe_path(path)
                with open(full, "w", encoding="utf-8", newline="") as stream:
                    stream.write(text)
                updated.append(path)
            with vault._lock:
                index = vault._repo.index
            index.remove([old], working_tree=False)
            index.add([new, *updated])
            if old_text != original_old_text:
                with open(new_full, "w", encoding="utf-8", newline="") as stream:
                    stream.write(old_text)
                index.add([new])
            actor = git.Actor("owner", "glacier@localhost")
            message = f"[owner] rename {old} to {new}\n\n{FROM_TRAILER}{old}\n{TO_TRAILER}{new}\n"
            commit = index.commit(message, author=actor, committer=actor)
        except Exception:
            # Drop anything staged for this rename; the working tree is restored below.
            try:
                with vault._lock:
                    vault._repo.index.reset()
            except Exception:
                pass
            # Restore the working tree if the one Git transaction could not be saved.
            if os.path.exists(new_full):
                os.makedirs(os.path.dirname(old_full), exist_ok=True)
                os.replace(new_full, old_full)
            for path, original in ((path, text) for path, text, _ in notes if path in rewrites):
                with open(vault.safe_path(path), "w", encoding="utf-8", newline="") as stream:
                    stream.write(original)
            raise

        for path in [old, new, *updated]:
            with vault._note_metadata_cache_lock:
                vault._note_metadata_cache.pop(path, None)
        # Rebuild the small SQLite index from the committed markdown snapshot.
        connection = vault._db()
        try:
            for path in [old, new, *updated]:
                connection.execute("DELETE FROM fts WHERE path=?", (path,))
                connection.execute("DELETE FROM links WHERE src=?", (path,))
            for path in [new, *updated]:
                raw = vault.read_raw_note(path)
                _, body = memory_meta.parse(raw, path)
                connection.execute("INSERT INTO fts VALUES (?,?)", (path, body))
                for destination, _ in memory_links.parse_links(body):
                    connection.execute("INSERT INTO links VALUES (?,?)", (path, destination))
            for path, change in ((old, "deleted"), (new, "created"), *((path, "updated") for path in updated)):
                connection.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)",
                                   ("owner", "rename_note", json.dumps({"path": path, "commit": commit.hexsha[:8]})))
            connection.commit()
        finally:
            connection.close()
        events = [{"type": "memory", "path": path, "change": change, "author": "owner", "run_id": ""}
                  for path, change in ((old, "deleted"), (new, "created"), *((path, "updated") for path in updated))]

    try:
        import store
        for event in events:
            store.broadcaster.publish(event)
    except (ImportError, AttributeError):
        pass
    return {"path": new, "commit": commit.hexsha[:8]}


def renamed_paths(commit) -> tuple[str, str] | None:
    """(old, new) recorded in a rename commit made by rename(), else None."""
    message = getattr(commit, "message", "") or ""
    if not message.startswith("[owner] rename "):
        return None
    found = {}
    for line in message.splitlines():
        for key, prefix in (("from", FROM_TRAILER), ("to", TO_TRAILER)):
            if line.startswith(prefix):
                found[key] = line[len(prefix):].strip()
    return (found["from"], found["to"]) if "from" in found and "to" in found else None
