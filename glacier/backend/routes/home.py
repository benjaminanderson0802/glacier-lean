"""Read-only summary data for the Home screen."""
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

import claims
import memory_meta
import runner
import store
import system_check
import vault


router = APIRouter()
_LOCAL_AI_CACHE_SECONDS = 10
_local_ai_lock = threading.Lock()
_local_ai = {"online": None, "model": None}  # None = first probe still running
_local_ai_at = 0.0
_local_ai_refreshing = False


def _probe_local_ai() -> None:
    """Refresh using the system discovery code off-request so Home never waits on tool probes."""
    global _local_ai, _local_ai_at, _local_ai_refreshing
    try:
        result = system_check.check_system()
        ollama = (result.get("tools") or {}).get("ollama") or {}
        models = result.get("ollama_models") or []
        online = bool(ollama.get("found") and models)
        configured = os.environ.get("GLACIER_LOCAL_MODEL", "").strip()
        model = configured or (result.get("recommended") or {}).get("local_model")
        with _local_ai_lock:
            _local_ai = {"online": online, "model": model if online else None}
            _local_ai_at = time.monotonic()
    except Exception:
        # Keep the last known value on a transient probe error.
        with _local_ai_lock:
            _local_ai_at = time.monotonic()
    finally:
        with _local_ai_lock:
            _local_ai_refreshing = False


def _local_ai_status() -> dict:
    global _local_ai_refreshing
    with _local_ai_lock:
        if time.monotonic() - _local_ai_at >= _LOCAL_AI_CACHE_SECONDS and not _local_ai_refreshing:
            _local_ai_refreshing = True
            threading.Thread(target=_probe_local_ai, daemon=True).start()
        return dict(_local_ai)


def _name(env_id: str, graph: dict) -> str:
    name = graph.get("name")
    if name:
        return name
    try:
        return runner.load_env(env_id).get("name") or env_id
    except (FileNotFoundError, ValueError, TypeError):
        return env_id


def _iso(value) -> str:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            parsed = datetime.fromtimestamp(0, timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _recent_notes(max_commits: int = 300) -> list[dict]:
    """Latest change per Markdown note from the vault history (newest first, at most 10).

    Git work happens under the vault lock (see vault.py access policy); the history scan is bounded.
    """
    changed: list[tuple[str, str]] = []
    seen = set()
    try:
        with vault._lock:
            for commit in vault._repo.iter_commits(max_count=max_commits):
                parents = commit.parents[:1]
                diffs = commit.tree.diff(parents[0].tree) if parents else commit.tree.diff(NULL_TREE)
                at = commit.committed_datetime.astimezone(timezone.utc).isoformat()
                for path in sorted({(d.b_path or d.a_path or "").replace("\\", "/") for d in diffs}):
                    if path.endswith(".md") and path not in seen and not path.startswith("claims/"):
                        seen.add(path)
                        changed.append((path, at))
                if len(changed) >= 10:
                    break
    except Exception:
        pass
    notes = []
    for path, at in changed[:10]:
        try:
            _, body = memory_meta.parse(vault.read_raw_note(path), path)
        except (OSError, ValueError):
            continue
        summary = next((re.sub(r"\s+", " ", line).strip(" #") for line in body.splitlines()
                        if line.strip() and not line.lstrip().startswith(("#", "-", "*"))), "")
        if not summary:
            summary = next((line.strip().lstrip("# ") for line in body.splitlines() if line.strip()), "")
        notes.append({"path": path, "summary": summary[:240], "at": at})
    return notes


@router.get("/api/home")
def home():
    """Return the latest run, claim, local model and memory summary in one call."""
    runs = store.list_runs(None)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    running = []
    needs_you = []

    for row in runs:
        status = row.get("status")
        run_id, env_id = row["run_id"], row["env_id"]
        try:
            graph = store.graph_of(run_id)
        except (KeyError, TypeError, json.JSONDecodeError):
            graph = {}
        name = _name(env_id, graph)
        if status in ("running", "queued", "waiting"):
            current = store.get_run(run_id) or {}
            states = current.get("node_states") or {}
            running.append({
                "run_id": run_id, "env_id": env_id, "name": name, "status": status,
                "step": sum(state == "done" for state in states.values()),
                "steps": len(graph.get("nodes") or []), "started_at": _iso(row.get("started_at")),
            })
        if status == "waiting":
            current = store.get_run(run_id) or {}
            needs_you.append({
                "kind": "approval", "title": "approval waiting", "detail": name,
                "at": _iso(row.get("started_at")),
                "ref": {"run_id": run_id, **({"node_id": current["waiting_on"]} if current.get("waiting_on") else {}),
                        "env_id": env_id},
            })
        elif status == "failed":
            try:
                started = datetime.fromisoformat(str(row.get("started_at", "")).replace("Z", "+00:00"))
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if started >= cutoff:
                needs_you.append({"kind": "failed_run", "title": "run failed", "detail": name,
                                  "at": _iso(started), "ref": {"run_id": run_id, "env_id": env_id}})

    for item in claims.list_claims("proposed"):
        cid = item.get("id") or ""
        try:
            full = claims.get_claim(cid)["meta"]
        except (ValueError, FileNotFoundError):
            full = item
        ref = {"claim_id": cid}
        if full.get("run_id"):
            ref["run_id"] = full["run_id"]
        if full.get("node_id"):
            ref["node_id"] = full["node_id"]
        needs_you.append({"kind": "claim", "title": item.get("kind") or "claim", "detail": item.get("summary") or "",
                          "at": _iso(full.get("updated")), "ref": ref})

    needs_you.sort(key=lambda item: item["at"], reverse=True)
    running.sort(key=lambda item: item["started_at"], reverse=True)
    import teams
    return {"local_ai": _local_ai_status(),
            "counts": {"running": len(running), "need_you": len(needs_you)},
            "needs_you": needs_you[:20], "running": running,
            "teams_running": _teams_running(),
            "recent_notes": _recent_notes()}


try:
    from git.objects.tree import NULL_TREE
except ImportError:  # pragma: no cover - GitPython currently exports NULL_TREE here
    NULL_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _teams_running() -> list[dict]:
    """Build teams that are running, waiting or need the owner; Home stays usable if the team store fails."""
    try:
        import teams
        return teams.summary()
    except Exception:
        logging.getLogger(__name__).warning("Could not read Build team status for Home", exc_info=True)
        return []
