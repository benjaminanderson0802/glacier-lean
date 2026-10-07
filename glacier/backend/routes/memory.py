"""Memory v2 API over the plain-file, git-backed vault."""
import os
import re
from datetime import timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import vault
import memory_meta

def _is_claims_path(path: str) -> bool:
    """Claims are never edited through memory; compare without case and with either slash (Windows/macOS ignore case)."""
    p = str(path).replace("\\", "/").casefold().lstrip("./")
    return p == "claims" or p.startswith("claims/")


router = APIRouter()


class NoteWrite(BaseModel):
    path: str
    body: str
    author: str
    model_config = {"extra": "forbid"}


class Undo(BaseModel):
    path: str
    commit: str | None = None


def _path(path: str) -> str:
    try:
        full = vault.safe_path(path)
    except ValueError as exc:
        raise HTTPException(400, "That note path is not allowed") from exc
    if not os.path.relpath(full, vault.VAULT).endswith(".md"):
        raise HTTPException(400, "Memory notes must be Markdown files")
    return full


def _normalised_path(path: str) -> str:
    full = _path(path)
    relative = os.path.relpath(full, vault.VAULT).replace(os.sep, "/")
    if _is_claims_path(relative):
        raise HTTPException(400, "Claims can't be edited from memory")
    return relative


def _meta(text: str, path: str) -> tuple[dict, str]:
    return memory_meta.parse(text, path)


def _links(body: str) -> list[str]:
    return list(dict.fromkeys(x.strip().split("|", 1)[0].removesuffix(".md") for x in re.findall(r"\[\[([^\]]+)\]\]", body)))


def _all() -> list[dict]:
    result = []
    for path in vault.list_notes(".md"):
        try:
            meta, _ = vault.read_note_metadata(path)
            result.append({"path": path, **{k: meta[k] for k in ("title", "author", "updated", "tags")}})
        except (OSError, ValueError):
            continue
    return result


@router.get("/api/memory/notes")
def notes(tag: str = "", author: str = ""):
    return [n for n in _all() if (not tag or tag in n["tags"]) and (not author or author == n["author"])]


@router.get("/api/memory/note")
def note(path: str):
    _path(path)
    try:
        text = vault.read_raw_note(path)
    except (FileNotFoundError, IsADirectoryError):
        raise HTTPException(404, "Note not found")
    meta, body = _meta(text, path)
    outgoing = _links(body)
    incoming = []
    for other in vault.list_notes(".md"):
        if other == path:
            continue
        try:
            _, other_body = vault.read_note_metadata(other)
            if path.removesuffix(".md") in _links(other_body):
                incoming.append(other.removesuffix(".md"))
        except (OSError, ValueError):
            continue
    return {"path": path, "body": body, "meta": meta, "links_out": outgoing, "links_in": sorted(incoming)}


@router.put("/api/memory/note")
def put_note(item: NoteWrite):
    path = _normalised_path(item.path)
    if item.author != "owner":
        raise HTTPException(400, "Notes saved from the screen must be authored by owner")
    try:
        commit = vault.write_note(path, item.body, author=item.author)
    except ValueError as exc:
        raise HTTPException(400, "That note path is not allowed") from exc
    return {"path": path, "commit": commit}


@router.get("/api/memory/graph")
def graph(limit: int | None = None):
    if limit is not None and limit < 1:
        raise HTTPException(400, "Limit must be a positive number")
    nodes, edges = [], []
    known = set()
    items = _all()
    items.sort(key=lambda item: item["updated"], reverse=True)
    if limit is not None:
        items = items[:limit]
    refs = []
    for item in items:
        path = item["path"].removesuffix(".md")
        known.add(path)
        nodes.append({"id": path, "title": item["title"], "kind": "note", "author": item["author"]})
        edges.append({"source": path, "target": item["author"], "kind": "wrote"})
        try:
            _, body = vault.read_note_metadata(item["path"])
            refs.extend((path, ref) for ref in _links(body))
        except (OSError, ValueError):
            pass
    for source, target in refs:
        kind = "run" if target.startswith("runs/") else "flow" if target.startswith("environments/") or target.startswith("flows/") else "claim" if target.startswith("claims/") else "note"
        if target not in known:
            nodes.append({"id": target, "title": os.path.basename(target), "kind": kind, "author": ""})
            known.add(target)
        edges.append({"source": source, "target": target, "kind": "link"})
    return {"nodes": nodes, "edges": edges}


@router.get("/api/memory/history")
def history(path: str):
    _path(path)
    try:
        with vault._lock:
            commits = list(vault._repo.iter_commits(paths=path))
    except Exception:
        commits = []
    return [{"commit": c.hexsha[:8], "author": c.author.name, "date": c.committed_datetime.astimezone(timezone.utc).isoformat(), "message": c.message.strip()} for c in commits]


@router.post("/api/memory/undo")
def undo(item: Undo):
    path = _normalised_path(item.path)
    if item.commit and not re.fullmatch(r"[0-9a-fA-F]{7,40}", item.commit):
        raise HTTPException(400, "Enter at least 7 letters or numbers from the saved version ID.")
    with vault._lock:
        commits = list(vault._repo.iter_commits(paths=path))
    if not commits:
        raise HTTPException(404, "No saved version exists for this note")
    matching = [c for c in commits if item.commit and c.hexsha.startswith(item.commit.lower())] if item.commit else []
    if item.commit and not matching:
        raise HTTPException(404, "That saved version was not found")
    if len(matching) > 1:
        raise HTTPException(400, "More than one saved version matches. Enter more of the version ID.")
    selected = matching[0] if item.commit else commits[0]
    target = selected.parents[0] if selected.parents else None
    if target is None:
        raise HTTPException(400, "There is no earlier version to restore")
    try:
        with vault._lock:
            previous = target.tree / path
            body = previous.data_stream.read().decode("utf-8")
    except (KeyError, OSError):
        raise HTTPException(404, "The earlier version did not contain this note")
    commit = vault.write_note(path, body, author="owner")
    return {"path": path, "commit": commit}


@router.get("/api/memory/search")
def search(q: str = "", mode: str = "keyword"):
    if mode not in ("keyword", "meaning"):
        raise HTTPException(400, "Search mode must be keyword or meaning")
    fallback = False
    found = []
    if mode == "meaning":
        try:
            import memory_index
            found = memory_index.search(q, k=10)
        except Exception:
            fallback = True
    if mode == "keyword" or fallback:
        found = vault.search(q, 10)
    results = []
    for entry in found:
        path, score = entry if isinstance(entry, (tuple, list)) else (entry, 0)
        try:
            _path(path)
            text = vault.read_raw_note(path)
        except (HTTPException, OSError, ValueError):
            continue
        meta, body = _meta(text, path)
        snippet = re.sub(r"\s+", " ", body).strip()[:240]
        row = {"path": path, "title": meta["title"], "score": float(score or 0), "snippet": snippet}
        if fallback:
            row["fallback"] = True
        results.append(row)
    return results
