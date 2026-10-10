"""Installed venture manifests and the small actions needed to run them."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

import audit_log
import runner
import secrets_store
import store
import vault
from app_paths import app_data_home


router = APIRouter()
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
_STEP_ID = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")


class CompleteStep(BaseModel):
    value: str | None = None
    model_config = ConfigDict(extra="forbid")


class RunVenture(BaseModel):
    dry_run: bool = True
    model_config = ConfigDict(extra="forbid")


def _venture_dir(slug: str) -> Path:
    root = (app_data_home() / "ventures").resolve()
    directory = root / slug
    try:
        directory.resolve().relative_to(root)
    except ValueError as error:
        raise HTTPException(404, "Venture not found") from error
    return directory


def _manifest_path(slug: str) -> Path:
    return _venture_dir(slug) / "venture.json"


def _read_manifest(slug: str) -> dict:
    if not _SLUG.fullmatch(slug):
        raise HTTPException(404, "Venture not found")
    path = _manifest_path(slug)
    try:
        path.resolve().relative_to(_venture_dir(slug).resolve())
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise HTTPException(404, "Venture not found") from error
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(422, "This venture manifest could not be read") from error
    except ValueError as error:
        raise HTTPException(404, "Venture not found") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("your_steps", []), list):
        raise HTTPException(422, "This venture manifest has an invalid shape")
    manifest.setdefault("slug", slug)
    if manifest["slug"] != slug:
        raise HTTPException(422, "This venture manifest has a mismatched name")
    return manifest


def _flow_ref(value) -> tuple[str | None, str | None]:
    if isinstance(value, str):
        return value, None
    if not isinstance(value, dict):
        return None, None
    env_id = value.get("env_id") or value.get("flow_id") or value.get("id") or value.get("flow")
    dry_id = value.get("dry_run_env_id") or value.get("dry_run_flow") or value.get("dry_run")
    return (env_id if isinstance(env_id, str) else None,
            dry_id if isinstance(dry_id, str) else None)


def _flows(manifest: dict) -> list[dict]:
    rows = []
    raw = manifest.get("flows", [])
    if not isinstance(raw, list):
        return rows
    for value in raw:
        env_id, dry_id = _flow_ref(value)
        if env_id:
            rows.append({"env_id": env_id, "dry_run_env_id": dry_id})
    root_dry_run = manifest.get("dry_run_env_id") or manifest.get("dry_run_flow")
    if rows and not rows[0].get("dry_run_env_id") and isinstance(root_dry_run, str):
        rows[0]["dry_run_env_id"] = root_dry_run
    return rows


def _flow_ids(manifest: dict) -> list[str]:
    ids = []
    for ref in _flows(manifest):
        for env_id in (ref.get("env_id"), ref.get("dry_run_env_id")):
            if env_id and env_id not in ids:
                ids.append(env_id)
    return ids


def _progress_path(slug: str) -> Path:
    return _venture_dir(slug) / "progress.json"


def _progress(slug: str) -> dict:
    try:
        value = json.loads(_progress_path(slug).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def _save_progress(slug: str, value: dict) -> None:
    path = _progress_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".progress-", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _next_cron(cron: str, now: datetime) -> str | None:
    """Find the next UTC cron match for the numeric 5- or 6-field syntax DBOS uses."""
    fields = cron.split()
    if len(fields) not in (5, 6):
        return None
    ranges = [(0, 59), (0, 59), (0, 23), (1, 31), (1, 12), (0, 7)] if len(fields) == 6 else [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
    def values(field: str, low: int, high: int) -> set[int] | None:
        result: set[int] = set()
        try:
            for part in field.split(","):
                base, slash, step_text = part.partition("/")
                step = int(step_text) if slash else 1
                if step < 1:
                    return None
                if base == "*":
                    start, stop = low, high
                elif "-" in base:
                    left, right = base.split("-", 1); start, stop = int(left), int(right)
                else:
                    start = stop = int(base)
                if start < low or stop > high or start > stop:
                    return None
                result.update(range(start, stop + 1, step))
        except ValueError:
            return None
        return result
    choices = [values(field, *limits) for field, limits in zip(fields, ranges)]
    if any(choice is None for choice in choices):
        return None
    choices = list(choices)
    day_index = 5 if len(fields) == 6 else 4
    if 7 in choices[day_index]:
        choices[day_index].discard(7); choices[day_index].add(0)
    current = now.astimezone(timezone.utc).replace(microsecond=0)
    current += timedelta(seconds=1 if len(fields) == 6 else 60 - current.second)
    if len(fields) == 5:
        current = current.replace(second=0)
    for _ in range(366 * 24 * 60 * (60 if len(fields) == 6 else 1)):
        parts = [current.second, current.minute, current.hour, current.day, current.month, (current.weekday() + 1) % 7]
        offset = 0 if len(fields) == 6 else 1
        matches = [parts[offset + index] in choice for index, choice in enumerate(choices)]
        if len(fields) == 5 and fields[2] != "*" and fields[4] != "*":
            day_matches = matches[2] or matches[4]
            matches[2] = matches[4] = day_matches
        if all(matches):
            return current.isoformat()
        current += timedelta(seconds=1 if len(fields) == 6 else 60)
    return None


def _venture_row(manifest: dict, now: datetime) -> dict:
    slug = manifest["slug"]
    progress = _progress(slug)
    steps = []
    for step in manifest.get("your_steps", []):
        if not isinstance(step, dict) or not isinstance(step.get("id"), str):
            continue
        item = dict(step)
        item["title"] = str(item.get("title") or "your step").lower()
        item["done"] = bool(progress.get(item["id"], item.get("done", False)))
        if not item.get("instructions"):
            item["instructions"] = str(item.get("detail") or item.get("instruction") or "")
        if not item.get("secret_name") and isinstance(item.get("secret"), str):
            item["secret_name"] = item["secret"]
        links = item.get("links")
        item["links"] = [link for link in links if isinstance(link, str)] if isinstance(links, list) else []
        if isinstance(item.get("link"), str) and item["link"] not in item["links"]:
            item["links"].append(item["link"])
        if isinstance(item.get("url"), str) and item["url"] not in item["links"]:
            item["links"].append(item["url"])
        steps.append(item)

    refs = _flows(manifest)
    envs, run_rows, next_runs = [], [], []
    flow_ids = _flow_ids(manifest)
    for env_id in flow_ids:
        try:
            graph = runner.load_env(env_id)
        except (FileNotFoundError, ValueError, TypeError):
            continue
        envs.append(graph)
        for node in graph.get("nodes", []):
            if node.get("type") == "schedule":
                cron = (node.get("config") or {}).get("cron")
                if cron:
                    upcoming = _next_cron(str(cron), now)
                    if upcoming:
                        next_runs.append(upcoming)
        run_rows.extend(store.list_runs(env_id))
    today_key = now.astimezone(timezone.utc).date()
    todays = []
    for row in run_rows:
        try:
            started = datetime.fromisoformat(str(row.get("started_at", "")).replace("Z", "+00:00"))
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if started.astimezone(timezone.utc).date() == today_key:
            todays.append(row)
    if flow_ids and len(envs) == len(flow_ids) and all(env.get("enabled", True) is False for env in envs):
        status = "paused"
    elif any(row.get("status") == "waiting" for row in run_rows):
        status = "needs_you"
    elif not flow_ids or len(envs) != len(flow_ids) or (steps and not all(step["done"] for step in steps)):
        status = "setting_up"
    else:
        status = "running"
    schedule = manifest.get("schedule")
    schedules = []
    if isinstance(schedule, str):
        schedules.append(schedule)
    elif isinstance(schedule, dict) and isinstance(schedule.get("cron"), str):
        schedules.append(schedule["cron"])
    elif isinstance(schedule, list):
        schedules.extend(item.get("cron") for item in schedule if isinstance(item, dict) and isinstance(item.get("cron"), str))
    if not next_runs:
        next_runs.extend(value for value in (_next_cron(cron, now) for cron in schedules) if value)
    today = {
        "runs": len(todays),
        "completed": sum(row.get("status") == "done" for row in todays),
        "failed": sum(row.get("status") == "failed" for row in todays),
    }
    report_path = manifest.get("daily_report")
    if isinstance(report_path, str) and report_path:
        root = (_manifest_path(slug).parent).resolve()
        report = (root / report_path).resolve()
        try:
            report.relative_to(root)
            data = json.loads(report.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if data.get("date") in (None, today_key.isoformat()):
                    counts = data.get("counts") if isinstance(data.get("counts"), dict) else data
                    for key, value in counts.items():
                        if isinstance(key, str) and isinstance(value, (int, float)) and not isinstance(value, bool):
                            today[key] = value
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return {
        "slug": slug,
        "name": str(manifest.get("name") or slug).lower(),
        "status": status,
        "flows": refs,
        "schedule": manifest.get("schedule"),
        "next_run": min(next_runs) if next_runs and status != "paused" else None,
        "today": today,
        "your_steps": steps,
    }


def list_ventures() -> list[dict]:
    folder = app_data_home() / "ventures"
    if not folder.is_dir():
        return []
    now = datetime.now(timezone.utc)
    rows = []
    for path in sorted(folder.iterdir()):
        if not path.is_dir() or not _SLUG.fullmatch(path.name):
            continue
        try:
            rows.append(_venture_row(_read_manifest(path.name), now))
        except HTTPException:
            continue
    return rows


def setup_items() -> list[dict]:
    items = []
    at = datetime.now(timezone.utc).isoformat()
    for venture in list_ventures():
        for step in venture["your_steps"]:
            if step.get("done"):
                continue
            items.append({
                "kind": "your_step", "title": str(step.get("title") or "Your step"),
                "detail": str(step.get("instructions") or venture["name"]), "at": at,
                "instructions": str(step.get("instructions") or ""),
                "links": step.get("links", []),
                "secret_name": step.get("secret_name"),
                "venture_slug": venture["slug"], "step_id": step["id"],
                "ref": {"venture_slug": venture["slug"], "step_id": step["id"]},
            })
    return items


@router.get("/api/ventures")
def ventures():
    return list_ventures()


@router.post("/api/ventures/{slug}/steps/{step_id}/done")
def complete_step(slug: str, step_id: str, body: CompleteStep):
    manifest = _read_manifest(slug)
    if not _STEP_ID.fullmatch(step_id):
        raise HTTPException(404, "Step not found")
    step = next((item for item in manifest.get("your_steps", []) if isinstance(item, dict) and item.get("id") == step_id), None)
    if step is None:
        raise HTTPException(404, "Step not found")
    secret_name = step.get("secret_name") or step.get("secret")
    if secret_name:
        if not isinstance(secret_name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", secret_name):
            raise HTTPException(422, "This step has an invalid secret name")
        if body.value is None or not body.value:
            raise HTTPException(400, "Paste the key before marking this step done")
        try:
            secrets_store.set(secret_name, body.value)
        except Exception as error:
            raise HTTPException(500, "Could not save this key in the operating-system keychain") from error
        audit_log.record("secret.set", what={"name": secret_name, "venture": slug})
    elif body.value is not None:
        raise HTTPException(400, "This step does not accept a key")

    progress = _progress(slug)
    progress[step_id] = True
    _save_progress(slug, progress)
    run_id, node_id = step.get("run_id"), step.get("node_id")
    if run_id and node_id:
        run = store.get_run(str(run_id))
        if not run or run.get("waiting_on") != node_id:
            raise HTTPException(409, "The run is no longer waiting on this step")
        from dbos import DBOS
        DBOS.send(str(run_id), {"approved": True}, topic=str(node_id))
        audit_log.record("run.approved", what={"run_id": str(run_id), "node_id": str(node_id), "approved": True})
    elif body.value is None and step.get("approval"):
        raise HTTPException(409, "This approval step is missing its run reference")
    return {"done": True, "secret_name": secret_name}


def _set_venture_paused(slug: str, paused: bool) -> dict:
    manifest = _read_manifest(slug)
    refs = _flows(manifest)
    if not refs:
        raise HTTPException(409, "This venture has no installed flows")
    graphs = []
    flow_ids = _flow_ids(manifest)
    for env_id in flow_ids:
        try:
            graph = runner.load_env(env_id)
        except (FileNotFoundError, ValueError, TypeError) as error:
            raise HTTPException(409, f"Flow {env_id} is not installed") from error
        graph["enabled"] = not paused
        graphs.append(graph)
    for graph in graphs:
        commit = vault.write_note(runner.env_path(graph["id"]), json.dumps(graph, indent=2), agent="owner")
        runner.sync_schedule(graph)
        audit_log.record("venture.paused" if paused else "venture.resumed",
                         what={"venture": slug, "env_id": graph["id"], "commit": commit})
    return {"paused": paused, "flows": [graph["id"] for graph in graphs]}


@router.post("/api/ventures/{slug}/pause")
def pause_venture(slug: str):
    return _set_venture_paused(slug, True)


@router.post("/api/ventures/{slug}/resume")
def resume_venture(slug: str):
    return _set_venture_paused(slug, False)


@router.post("/api/ventures/{slug}/run")
def run_venture(slug: str, body: RunVenture):
    manifest = _read_manifest(slug)
    if not body.dry_run:
        raise HTTPException(400, "Venture runs from this screen must use the dry-run flow")
    refs = _flows(manifest)
    ref = next((item for item in refs if item.get("dry_run_env_id")), None)
    if ref is None:
        raise HTTPException(409, "This venture does not have a dry-run flow")
    env_id = ref["dry_run_env_id"]
    try:
        runner.load_env(env_id)
        run_id = runner.start_run(env_id, {"_venture": slug, "_dry_run": body.dry_run})
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(409, f"Flow {env_id} is not installed") from error
    audit_log.record("run.started", what={"venture": slug, "env_id": env_id, "run_id": run_id,
                                           "source": "venture", "dry_run": body.dry_run})
    return {"run_id": run_id, "env_id": env_id, "dry_run": body.dry_run}


def approval_steps() -> list[dict]:
    needs = []
    for row in store.list_runs(None):
        if row.get("status") != "waiting":
            continue
        current = store.get_run(row["run_id"]) or {}
        run_id, node_id = row["run_id"], current.get("waiting_on")
        if not node_id:
            continue
        try:
            graph = store.graph_of(run_id)
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        node = next((item for item in graph.get("nodes", []) if item.get("id") == node_id), None)
        prompt = str(((node or {}).get("config") or {}).get("prompt") or "")
        if not prompt.startswith("Your step:"):
            continue
        needs.append({"kind": "your_step", "title": prompt.splitlines()[0].lower(), "detail": prompt,
                      "instructions": prompt, "links": re.findall(r"https?://[^\s<>()]+", prompt),
                      "at": row.get("started_at", ""),
                      "ref": {"run_id": run_id, "node_id": node_id, "env_id": row["env_id"]}})
    return needs


def install_manifests(home: str, bundled_root: Path | None = None) -> None:
    """Copy bundled venture manifests into a new Glacier home without replacing owner data."""
    bundled = (Path(bundled_root) if bundled_root is not None else Path(__file__).resolve().parents[3] / "ventures")
    if not bundled.is_dir():
        return
    destination = Path(home).resolve() / "ventures"
    for source in bundled.glob("*/venture.json"):
        if not _SLUG.fullmatch(source.parent.name):
            continue
        target = destination / source.parent.name / "venture.json"
        if target.exists():
            continue
        try:
            target.parent.resolve().relative_to(destination.resolve())
        except ValueError:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(source.read_bytes())
        except OSError:
            # A read-only home should not prevent the rest of the backend from starting.
            continue
