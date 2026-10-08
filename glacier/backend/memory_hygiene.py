"""Proposal-only cleanup suggestions for the plain-file memory vault."""

import datetime as dt
import hashlib
import json
import os
import re

import vault


def _home():
    return os.path.abspath(os.environ.get("GLACIER_HOME", "data"))


def _state_path():
    return os.path.join(_home(), "hygiene.json")


def _load():
    try:
        with open(_state_path(), encoding="utf-8") as state:
            data = json.load(state)
        return data if isinstance(data, dict) else {"proposals": []}
    except (OSError, ValueError):
        return {"proposals": []}


def _save(data):
    os.makedirs(_home(), exist_ok=True)
    temporary = _state_path() + ".tmp"
    with open(temporary, "w", encoding="utf-8") as state:
        json.dump(data, state, indent=2, sort_keys=True)
        state.write("\n")
    os.replace(temporary, _state_path())


def _body(raw):
    """Return note content without YAML front matter."""
    match = re.match(r"\A---\s*\r?\n.*?\r?\n---\s*(?:\r?\n|$)", raw, re.S)
    return raw[match.end():] if match else raw


def _metadata(raw):
    match = re.match(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", raw, re.S)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            result[key.strip()] = value.strip().strip("\"'")
    return result


def _date(raw, full_path):
    meta = _metadata(raw)
    value = meta.get("updated") or meta.get("created")
    if value:
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.timestamp()
        except ValueError:
            pass
    return os.path.getmtime(full_path)


def _id(kind, paths):
    key = kind + "\0" + "\0".join(sorted(paths))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _proposal(kind, paths, reason):
    paths = sorted(paths)
    return {"id": _id(kind, paths), "kind": kind, "paths": paths, "reason": reason}


def _public(proposal):
    return {key: proposal[key] for key in ("id", "kind", "paths", "reason")}


def _read_raw(path):
    read = getattr(vault, "read_raw_note", vault.read_note)
    return read(path)


def _eligible_merge_path(path):
    return not path.startswith(("claims/", "archive/"))


def _link_path(target):
    target = target.strip().replace("\\", "/").lstrip("/")
    return target if target.endswith(".md") else target + ".md"


def _rewrite_links(raw, removed_paths, keeper):
    removed = {_link_path(path) for path in removed_paths}

    def replace(match):
        target, suffix = match.groups()
        if _link_path(target) not in removed:
            return match.group(0)
        replacement = keeper if target.strip().endswith(".md") else keeper[:-3]
        return f"[[{replacement}{suffix}]]"

    return re.sub(r"\[\[([^\]|#]+)([^\]]*)\]\]", replace, raw)


def _linked_targets(raw):
    targets = set()
    for link in re.findall(r"\[\[([^\]|#]+)", raw):
        target = link.strip().replace("\\", "/").lstrip("/")
        if not target.endswith(".md"):
            target += ".md"
        targets.add(target)
    return targets


def _near_duplicate_pairs(notes, exact_groups):
    """Use the optional meaning index only when it is initialized and responsive."""
    try:
        import memory_index

        paths = {path for path, _ in notes}
        pairs = set()
        for path, body in notes:
            for other, score in memory_index.search(body.strip(), k=max(10, len(notes))):
                if other in paths and other != path and float(score) >= 0.95:
                    pair = tuple(sorted((path, other)))
                    pairs.add(pair)
        # Exact groups are handled as one proposal, never again as near duplicates.
        exact_members = {path for group in exact_groups for path in group}
        return [pair for pair in sorted(pairs) if not set(pair) <= exact_members]
    except Exception:
        return []


def scan():
    """Create and return pending proposals. This never edits vault notes."""
    prior = _load()
    by_id = {item.get("id"): item for item in prior.get("proposals", []) if isinstance(item, dict)}
    paths = vault.list_notes(".md")
    notes = []
    raw_by_path = {}
    for path in paths:
        try:
            raw = _read_raw(path)
        except (OSError, ValueError):
            continue
        raw_by_path[path] = raw
        if _eligible_merge_path(path):
            notes.append((path, _body(raw).strip()))

    grouped = {}
    for path, body in notes:
        if body:
            grouped.setdefault(body, []).append(path)
    exact_groups = [sorted(group) for group in grouped.values() if len(group) > 1]
    proposals = []
    for group in exact_groups:
        proposals.append(_proposal("merge", group, "These notes have the same content after front matter is removed."))

    exact_members = {path for group in exact_groups for path in group}
    for pair in _near_duplicate_pairs(notes, exact_groups):
        if not (set(pair) & exact_members):
            proposals.append(_proposal("merge", pair, "These notes have very similar content (score at least 0.95)."))

    try:
        stale_days = max(0, int(os.environ.get("GLACIER_STALE_DAYS", "90")))
    except ValueError:
        stale_days = 90
    cutoff = dt.datetime.now(dt.timezone.utc).timestamp() - stale_days * 86400
    incoming = set()
    for path, raw in raw_by_path.items():
        incoming.update(_linked_targets(raw))
    for path, raw in raw_by_path.items():
        if not path.startswith("runs/") or path in incoming:
            continue
        try:
            old = _date(raw, vault.safe_path(path)) < cutoff
        except (OSError, ValueError):
            old = False
        if old:
            proposals.append(_proposal("archive", [path], f"This run note is older than {stale_days} days and no other note links to it."))

    # Keep prior decisions and stable IDs; rejected/approved proposals never return.
    current = []
    for proposal in proposals:
        proposal["_snapshots"] = {
            path: hashlib.sha256(raw_by_path[path].encode("utf-8")).hexdigest()
            for path in proposal["paths"] if path in raw_by_path
        }
        old = by_id.get(proposal["id"])
        if old and old.get("status") in ("rejected", "approved"):
            continue
        current.append({**proposal, "status": "pending"})
    decided = [item for item in by_id.values() if item.get("status") in ("rejected", "approved")]
    _save({"proposals": decided + current})
    return [_public(item) for item in current]


def list_proposals():
    return [_public(item) for item in _load().get("proposals", []) if item.get("status") == "pending"]


def _commit_changes(changes, removals, agent="glacier-hygiene"):
    """Write a set of note changes and removals as one reversible git commit."""
    with vault._lock:
        touched = sorted(set(changes) | set(removals))
        if not touched:
            raise FileNotFoundError("the notes in this proposal are no longer available")
        original_files = {
            path: open(vault.safe_path(path), "rb").read()
            if os.path.exists(vault.safe_path(path)) else None
            for path in touched
        }
        changed_paths = []
        removed_paths = []
        index = vault._repo.index
        head = vault._repo.head.commit.hexsha
        try:
            for path, content in changes.items():
                full = vault.safe_path(path)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w", encoding="utf-8") as note:
                    note.write(content)
                changed_paths.append(path)
            for path in removals:
                full = vault.safe_path(path)
                if os.path.exists(full):
                    os.remove(full)
                    removed_paths.append(path)
            if not changed_paths and not removed_paths:
                raise FileNotFoundError("the notes in this proposal are no longer available")
            if changed_paths:
                index.add(changed_paths)
            if removed_paths:
                index.remove(removed_paths, working_tree=True)
            commit = index.commit(f"[{agent}] apply memory hygiene proposal")
        except Exception as exc:
            for path in touched:
                full = vault.safe_path(path)
                previous = original_files.get(path)
                if previous is None:
                    if os.path.exists(full):
                        os.remove(full)
                else:
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "wb") as note:
                        note.write(previous)
            if vault._repo.head.commit.hexsha != head:
                vault._repo.git.reset("--soft", head)
            vault._repo.git.reset("HEAD", "--", *touched)
            index.reset()
            raise ValueError("the memory changes could not be saved. Your notes were restored; please try again.") from exc

        vault.invalidate_note_history(touched)
        # The Git commit is authoritative. Update the rebuildable SQLite views
        # afterward, so an index failure cannot roll files back behind HEAD.
        connection = vault._db()
        try:
            for path in removed_paths:
                connection.execute("DELETE FROM fts WHERE path=?", (path,))
                connection.execute("DELETE FROM links WHERE src=?", (path,))
                connection.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)",
                                   (agent, "delete_note", json.dumps({"path": path, "commit": commit.hexsha[:8]})))
            for path in changed_paths:
                content = changes[path]
                connection.execute("DELETE FROM fts WHERE path=?", (path,))
                connection.execute("INSERT INTO fts VALUES (?,?)", (path, content))
                connection.execute("DELETE FROM links WHERE src=?", (path,))
                for target in re.findall(r"\[\[([^\]|#]+)", content):
                    connection.execute("INSERT INTO links VALUES (?,?)", (path, target.strip()))
                connection.execute("INSERT INTO events(agent,kind,data) VALUES (?,?,?)",
                                   (agent, "write_note", json.dumps({"path": path, "commit": commit.hexsha[:8]})))
            connection.commit()
        finally:
            connection.close()

    # Live memory events (same shape as vault.write_note), published outside the vault lock.
    try:
        import store
        for path in changed_paths:
            store.broadcaster.publish({"type": "memory", "path": path,
                                       "change": "created" if original_files.get(path) is None else "updated",
                                       "author": agent, "run_id": ""})
        for path in removed_paths:
            store.broadcaster.publish({"type": "memory", "path": path, "change": "deleted", "author": agent, "run_id": ""})
    except (ImportError, AttributeError):
        pass
    return commit.hexsha[:8]


def decide(proposal_id, approve):
    state = _load()
    proposals = state.get("proposals", [])
    proposal = next((item for item in proposals if item.get("id") == proposal_id), None)
    if proposal is None:
        raise FileNotFoundError("proposal not found")
    if proposal.get("status") != "pending":
        return {"id": proposal_id, "status": proposal["status"]}
    commit = None
    if approve:
        paths = proposal["paths"]
        try:
            for path in paths:
                current = _read_raw(path)
                expected = proposal.get("_snapshots", {}).get(path)
                if expected and hashlib.sha256(current.encode("utf-8")).hexdigest() != expected:
                    raise ValueError("a note changed after this proposal was created; scan again before approving")
            if proposal["kind"] == "merge":
                existing = [(path, _read_raw(path)) for path in paths]
                existing.sort(key=lambda item: (_date(item[1], vault.safe_path(item[0])), item[0]))
                keeper, content = existing[0]
                additions = "".join(f"\n## Merged from {path}\n\n{body.strip()}\n" for path, body in existing[1:])
                removed_paths = [path for path, _ in existing[1:]]
                changes = {keeper: content.rstrip() + additions}
                for path in vault.list_notes(".md"):
                    if path == keeper or path in removed_paths:
                        continue
                    raw = _read_raw(path)
                    rewritten = _rewrite_links(raw, removed_paths, keeper)
                    if rewritten != raw:
                        changes[path] = rewritten
                commit = _commit_changes(changes, removed_paths)
            elif proposal["kind"] == "archive":
                source = paths[0]
                destination = "archive/" + source
                if os.path.exists(vault.safe_path(destination)):
                    raise ValueError("an archived note already exists at the destination")
                content = _read_raw(source)
                commit = _commit_changes({destination: content}, [source])
            else:
                raise ValueError("unknown proposal type")
        except (FileNotFoundError, ValueError) as exc:
            raise ValueError(f"proposal could not be applied: {exc}") from exc
        proposal["status"] = "approved"
        proposal["commit"] = commit
    else:
        proposal["status"] = "rejected"
    _save(state)
    return {"id": proposal_id, "status": proposal["status"], **({"commit": commit} if commit else {})}
