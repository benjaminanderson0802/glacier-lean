"""Memory v2 API over the plain-file, git-backed vault."""
import os
import re
from datetime import timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import vault
import memory_meta
from memory_links import LinkResolver, resolve_links

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


def _all() -> list[dict]:
    result = []
    for path in vault.list_notes(".md"):
        try:
            meta, _ = vault.read_note_metadata(path)
            result.append({"path": path, **{k: meta[k] for k in ("title", "author", "updated", "tags")}})
        except (OSError, ValueError):
            continue
    return result


def _link_index(items: list[dict]) -> tuple[dict[str, list[dict[str, str]]], LinkResolver]:
    paths = [item["path"].removesuffix(".md") for item in items]
    attachments = []
    for root, dirs, files in os.walk(vault.VAULT):
        dirs[:] = [name for name in dirs if name != ".git"]
        for name in files:
            if not name.lower().endswith(".md"):
                attachments.append(os.path.relpath(os.path.join(root, name), vault.VAULT).replace(os.sep, "/"))
    resolver = LinkResolver(paths, attachments)
    links = {}
    for item in items:
        path = item["path"].removesuffix(".md")
        try:
            _, body = vault.read_note_metadata(item["path"])
            links[path] = resolve_links(body, path, resolver)
        except (OSError, ValueError):
            links[path] = []
    return links, resolver


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
    items = _all()
    links, _ = _link_index(items)
    note_path = path.replace("\\", "/").removesuffix(".md")
    # Keep the requested on-disk identity while matching case-insensitively.
    note_path = next((p for p in links if p.casefold() == note_path.casefold()), note_path)
    outgoing = links.get(note_path, resolve_links(body, note_path, LinkResolver([])))
    incoming = sorted(source for source, targets in links.items()
                      if any(target["status"] == "resolved" and target["target"].casefold() == note_path.casefold()
                             for target in targets))
    return {"path": path, "body": body, "meta": meta,
            "links_out": [item["target"] for item in outgoing], "links_in": incoming,
            "links_out_status": [{**item, "display": item["target"] if item["status"] == "resolved"
                                  else f"{item['target']} (not written yet)"} for item in outgoing]}


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
    def _mtime(item: dict) -> int:
        try:
            return os.stat(vault.safe_path(item["path"])).st_mtime_ns
        except OSError:  # removed since it was listed
            return 0
    items.sort(key=_mtime, reverse=True)
    if limit is not None:
        items = items[:limit]
    links, _ = _link_index(items)
    for item in items:
        path = item["path"].removesuffix(".md")
        known.add(path)
        nodes.append({"id": path, "title": item["title"], "kind": "note", "author": item["author"]})
        edges.append({"source": path, "target": item["author"], "kind": "wrote"})
    for source, refs in links.items():
        for ref in refs:
            target = ref["target"]
            kind = ("unresolved" if ref["status"] == "unresolved" else
                    "run" if target.startswith("runs/") else
                    "flow" if target.startswith("environments/") or target.startswith("flows/") else
                    "claim" if target.startswith("claims/") else "note")
            if target not in known:
                nodes.append({"id": target, "title": os.path.basename(target), "kind": kind, "author": ""})
                known.add(target)
            edges.append({"source": source, "target": target, "kind": "link"})
    return {"nodes": nodes, "edges": edges}


@router.get("/api/memory/history")
def history(path: str):
    _path(path)
    # Commit details load lazily through the shared Git pipe, so read them while holding the lock.
    try:
        with vault._lock:
            return [{"commit": c.hexsha[:8], "author": c.author.name,
                     "date": c.committed_datetime.astimezone(timezone.utc).isoformat(),
                     "message": c.message.strip()} for c in vault._repo.iter_commits(paths=path)]
    except Exception:
        return []


@router.post("/api/memory/undo")
def undo(item: Undo):
    path = _normalised_path(item.path)
    if item.commit and not re.fullmatch(r"[0-9a-fA-F]{7,40}", item.commit):
        raise HTTPException(400, "Enter at least 7 letters or numbers from the saved version ID.")
    with vault._lock:
        commits = list(vault._repo.iter_commits(paths=path))
        if item.commit:
            import memory_rename
            requested = item.commit.lower()
            renames = [(commit, memory_rename.renamed_paths(commit)) for commit in vault._repo.iter_commits(paths=".")
                       if commit.hexsha.startswith(requested) and getattr(commit, "message", "").startswith("[owner] rename ")]
            if len(renames) == 1 and renames[0][1]:
                old_path, new_path = renames[0][1]
                # Undo a rename by renaming the note back: links that point at it follow it again,
                # nothing else in the vault is touched, and the undo is its own saved version.
                try:
                    result = memory_rename.rename(new_path, old_path)
                except FileNotFoundError as exc:
                    raise HTTPException(409, "That rename can't be undone because the note has moved or been removed since") from exc
                except FileExistsError as exc:
                    raise HTTPException(409, "That rename can't be undone because a note now uses the old name") from exc
                return {"path": item.path, "commit": result["commit"]}
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


@router.post("/api/memory/rename")
def rename_note(item: dict):
    from memory_rename import rename
    if set(item) != {"from", "to"} or not all(isinstance(item[key], str) for key in ("from", "to")):
        raise HTTPException(400, "Provide the old and new note paths")
    try:
        return rename(item["from"], item["to"])
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


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
            row["message"] = "Meaning search is unavailable. Showing keyword matches instead."
        results.append(row)
    return results
