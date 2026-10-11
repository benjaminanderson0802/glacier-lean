"""Validate and install manifest-listed venture flows into local Glacier."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import jsonschema

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SCHEMA_PATH = ROOT / "venture.schema.json"
NODE_TYPES_PATH = REPO / "glacier" / "contract" / "node_types.json"


def manifests(only: str | None = None, *, ready_only: bool = False) -> list[Path]:
    found = sorted(ROOT.glob("*/venture.json"))
    if only:
        found = [path for path in found if json.loads(path.read_text(encoding="utf-8")).get("slug") == only]
        if not found:
            raise ValueError(f"venture manifest not found: {only}")
    if not found:
        raise ValueError("no venture manifests found; no flows can be installed")
    if ready_only:
        found = [p for p in found if json.loads(p.read_text(encoding="utf-8")).get("status") == "ready"]
        if not found:
            raise ValueError("no ready venture manifests found")
    return found


def flow_file(manifest_path: Path, flow_ref: str) -> Path:
    """Resolve either the stable flow id or a legacy relative flow filename."""
    flows_dir = manifest_path.parent / "flows"
    candidates = [flows_dir / f"{flow_ref}.json", manifest_path.parent / flow_ref]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    for candidate in sorted(flows_dir.glob("*.json")):
        try:
            if json.loads(candidate.read_text(encoding="utf-8")).get("id") == flow_ref:
                return candidate
        except (OSError, json.JSONDecodeError):
            continue
    raise FileNotFoundError(f"{manifest_path.parent.name}: manifest flow is missing: {flow_ref}")


@lru_cache(maxsize=1)
def _catalog_types() -> set[str]:
    catalog = json.loads(NODE_TYPES_PATH.read_text(encoding="utf-8"))
    core_types = {entry["type"] for entry in catalog["types"]}
    backend = str(REPO / "glacier" / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    import plugins

    return core_types | {entry["type"] for entry in plugins.load_nodes(core_types)}


def validate_schedules(manifest: dict, flow: dict) -> None:
    flow_id = flow.get("id")
    declared = [row for row in manifest.get("schedules", []) if row.get("flow") == flow_id]
    schedule_nodes = [node for node in flow.get("nodes", []) if node.get("type") == "schedule"]
    if len(declared) != len(schedule_nodes):
        raise ValueError(f"{flow_id}: manifest schedule entries do not match schedule nodes")
    for row, node in zip(declared, schedule_nodes):
        config = node.get("config", {})
        if row["cron"] != config.get("cron"):
            raise ValueError(f"{flow_id}: manifest cron does not match schedule node")
        if row["missed_run"] != config.get("missed_run") or row["overlap"] != config.get("overlap"):
            raise ValueError(f"{flow_id}: manifest missed-run or overlap policy does not match schedule node")


def validate_all(only: str | None = None, *, ready_only: bool = False) -> list[dict]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    known_types = _catalog_types()
    checked: list[dict] = []
    slugs: set[str] = set()
    flow_ids: set[str] = set()
    for manifest_path in manifests(only, ready_only=ready_only):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)
        slug = manifest["slug"]
        if slug in slugs or slug != manifest_path.parent.name:
            raise ValueError(f"{manifest_path}: slug must be unique and match its directory")
        slugs.add(slug)
        declared_flows = set(manifest["flows"])
        declared_schedules = manifest.get("schedules", [])
        for flow_id in manifest["flows"]:
            flow_path = flow_file(manifest_path, flow_id)
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            if not isinstance(flow.get("id"), str) or not flow.get("id"):
                raise ValueError(f"{flow_path}: flow has no id")
            if not isinstance(flow.get("nodes"), list) or not isinstance(flow.get("edges"), list):
                raise ValueError(f"{flow_path}: flow must contain node and edge lists")
            if flow["id"] in flow_ids:
                raise ValueError(f"duplicate environment id: {flow['id']}")
            flow_ids.add(flow["id"])
            for node in flow["nodes"]:
                node_type = node.get("type") if isinstance(node, dict) else None
                if node_type not in known_types:
                    raise ValueError(f"{flow_path}: unknown node type {node_type!r}")
            validate_schedules(manifest, flow)
            checked.append({"venture": slug, "flow": flow_id, "validated": True})
        if any(row.get("flow") not in declared_flows for row in declared_schedules):
            raise ValueError(f"{slug}: schedule references an undeclared flow")
    return checked


def _engine_token() -> str:
    if os.environ.get("GLACIER_TOKEN", "").strip():
        return os.environ["GLACIER_TOKEN"].strip()
    home = Path(os.environ.get("GLACIER_HOME", "data"))
    token_path = home / ".engine-token"
    if not token_path.is_file():
        raise FileNotFoundError(f"Glacier engine token not found: {token_path}")
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"Glacier engine token is empty: {token_path}")
    return token


def engine_token() -> str:
    """Compatibility alias for callers of the original installer helper."""
    return _engine_token()


def shlex_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _runtime_flow(flow: dict, *, repo_root: Path, slug: str, home: Path) -> dict:
    """Bind source commands to this checkout and its interpreter for the installed flow."""
    result = json.loads(json.dumps(flow))
    venture_cwd = repo_root / "ventures" / slug
    python = python_command()
    # Windows Python expects drive paths and semicolon separators even when its
    # command is launched through Git Bash. Forward slashes keep Git Bash's path
    # converter from rewriting the PYTHONPATH value to /c/... for native Python.
    import_path = os.pathsep.join(
        path.replace("\\", "/") for path in (str(repo_root), str(venture_cwd))
    )

    def bind_command(command: str) -> str:
        command = command.replace("{python}", python)
        command = command.replace("PYTHONPATH=. .venv/bin/python", f"PYTHONPATH={shlex_quote(import_path)} {python}")
        command = re.sub(
            r"(?<![A-Za-z0-9_./-])python3?(?=\s)",
            lambda _match: python,
            command,
        )
        # Flow commands often quote this shell variable themselves. Replace the
        # whole quoted expression so the shlex-quoted interpreter is not nested
        # inside literal double quotes (which makes the quotes part of its name).
        command = command.replace(
            '"${GLACIER_PYTHON:-$HOME/w/glacier-lean/.venv/bin/python}"', python
        )
        command = command.replace('"$HOME/w/glacier-lean/.venv/bin/python"', python)
        command = command.replace("${GLACIER_PYTHON:-$HOME/w/glacier-lean/.venv/bin/python}", python)
        return command.replace("$HOME/w/glacier-lean/.venv/bin/python", python)

    for node in result.get("nodes", []):
        if node.get("type") != "command":
            continue
        config = node.setdefault("config", {})
        requested_cwd = str(config.get("cwd") or "").strip()
        if requested_cwd in ("", ".", "{repo}"):
            config["cwd"] = str(repo_root)
        elif requested_cwd == f"ventures/{slug}":
            staged = home / "workspaces" / str(flow.get("id")) / "ventures" / slug
            config["cwd"] = str(staged if staged.is_dir() else venture_cwd)
        elif requested_cwd.startswith("/home/") and f"/ventures/{slug}" in requested_cwd:
            config["cwd"] = str(venture_cwd)
        command = str(config.get("cmd") or "")
        if command:
            path_append = f"${{PYTHONPATH:+{shlex_quote(os.pathsep)}$PYTHONPATH}}"
            config["cmd"] = f"export PYTHONPATH={shlex_quote(import_path)}{path_append}; {bind_command(command)}"
    for key in ("acceptance", "checks"):
        rows = result.get(key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and isinstance(row.get("cmd"), str):
                    row["cmd"] = bind_command(row["cmd"])
    return result


def python_command() -> str:
    """Compatibility helper returning the interpreter used for installed flows."""
    # Git Bash can execute a drive-letter path with forward slashes directly;
    # keeping it quoted handles spaces in the interpreter's installation path.
    return shlex_quote(sys.executable.replace("\\", "/"))


def discover_flows(only: str | None = None) -> list[tuple[Path, dict]]:
    """Compatibility view of manifest flows with checkout-bound commands."""
    if only and not any(json.loads(path.read_text(encoding="utf-8")).get("slug") == only for path in ROOT.glob("*/venture.json")):
        raise ValueError(f"No venture flows found for {only}")
    rows: list[tuple[Path, dict]] = []
    for manifest_path in manifests(only):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for flow_id in manifest["flows"]:
            flow = json.loads(flow_file(manifest_path, flow_id).read_text(encoding="utf-8"))
            runtime = json.loads(json.dumps(flow))
            for node in runtime.get("nodes", []):
                if node.get("type") != "command":
                    continue
                config = node.setdefault("config", {})
                if config.get("cwd") in ("{repo}", "", None):
                    config["cwd"] = str(REPO)
                command = str(config.get("cmd") or "")
                command = command.replace("{python}", python_command())
                command = re.sub(r"(?<![A-Za-z0-9_./-])python3?(?=\s)", python_command(), command)
                config["cmd"] = command
            rows.append((manifest_path, runtime))
    return rows


def _stage_scripts(venture_dir: Path, slug: str, home: Path, flow_ids: list[str]) -> None:
    source = venture_dir / "scripts"
    if not source.is_dir():
        return
    for flow_id in flow_ids:
        destination = home / "workspaces" / flow_id / "ventures" / slug / "scripts"
        destination.mkdir(parents=True, exist_ok=True)
        for script in source.glob("*.py"):
            shutil.copy2(script, destination / script.name)


def register_flow(api: str, token: str, flow: dict) -> dict:
    flow_id = flow.get("id")
    if not flow_id or not isinstance(flow.get("nodes"), list) or not isinstance(flow.get("edges"), list):
        raise ValueError("flow file must include id, nodes, and edges")
    request = Request(
        f"{api.rstrip('/')}/api/environments/{quote(str(flow_id), safe='')}",
        data=json.dumps(flow).encode("utf-8"), method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def register_flow_if_changed(api: str, token: str, flow: dict) -> dict:
    """Skip unchanged environments so repeated installs do not create extra revisions."""
    flow_id = flow.get("id")
    if not flow_id:
        raise ValueError("flow file must include an id")
    url = f"{api.rstrip('/')}/api/environments/{quote(str(flow_id), safe='')}"
    request = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(request, timeout=30) as response:
            current = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code != 404:
            raise
    else:
        # Reinstall must not undo a pause chosen in Glacier.
        if current.get("enabled") is False:
            flow = dict(flow, enabled=False)
        if current == flow:
            return {"saved": False, "unchanged": True}
    return register_flow(api, token, flow)


def install_flow(flow: dict, *, base: str, token: str) -> dict:
    """Compatibility helper for registering a single flow through idempotent PUT."""
    api = base[:-4] if base.endswith("/api") else base
    return register_flow(api, token, flow)


def install(api: str, token: str, only: str | None = None, *, home: Path | None = None,
            ready_only: bool = False, start: bool = False) -> list[dict]:
    validate_all(only, ready_only=ready_only)
    data_home = home or Path(os.environ.get("GLACIER_HOME", "data"))
    registered: list[dict] = []
    for manifest_path in manifests(only, ready_only=ready_only):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        slug = manifest["slug"]
        flow_ids = manifest["flows"]
        _stage_scripts(manifest_path.parent, slug, data_home, flow_ids)
        for flow_id in flow_ids:
            flow_path = flow_file(manifest_path, flow_id)
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            runtime = _runtime_flow(flow, repo_root=REPO, slug=slug, home=data_home)
            if ready_only:
                runtime = scheduled_flow(runtime)
            result = register_flow_if_changed(api, token, runtime)
            registered.append({"venture": slug, "flow": flow_id, "result": result})
        if ready_only:
            canary = health_flow(slug, api)
            result = register_flow_if_changed(api, token, canary)
            registered.append({"venture": slug, "flow": canary["id"], "result": result})
    if start:
        for row in registered:
            row["run"] = start_once(api, token, row["flow"])
    return registered


def api_json(api: str, token: str, path: str, *, method: str = "GET", body=None, timeout: int = 30):
    request = Request(api.rstrip("/") + path, method=method,
                      data=json.dumps(body).encode() if body is not None else None,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def scheduled_flow(flow: dict) -> dict:
    """Use DBOS for daily intake; an outstanding approval blocks overlapping runs."""
    result = json.loads(json.dumps(flow))
    if any(n["type"] == "schedule" for n in result["nodes"]):
        return result
    targets = {edge["target"] for edge in result["edges"]}
    roots = [node["id"] for node in result["nodes"] if node["id"] not in targets]
    if not roots:
        raise ValueError(f"{flow['id']}: cannot schedule a flow without an entry step")
    nid = "venture-daily-intake"
    if any(n["id"] == nid for n in result["nodes"]):
        raise ValueError(f"{flow['id']}: reserved schedule node id")
    result["nodes"].insert(0, {"id": nid, "type": "schedule", "position": {"x": -500, "y": 0},
                              "config": {"cron": "0 7 * * *", "missed_run": "run_once", "overlap": "skip"}})
    result["edges"].extend({"id": f"{nid}-{root}", "source": nid, "target": root} for root in roots)
    if "max_steps" in result:
        result["max_steps"] = int(result["max_steps"]) + 1
    return result


def start_once(api: str, token: str, flow_id: str) -> dict:
    path = f"/api/environments/{quote(flow_id, safe='')}"
    if api_json(api, token, path).get("enabled") is False:
        return {"state": "paused"}
    runs = api_json(api, token, f"/api/runs?env_id={quote(flow_id, safe='')}")
    active = next((row for row in runs if row["status"] in ("queued", "running", "waiting")), None)
    if active:
        return {"state": active["status"], "run_id": active["run_id"], "existing": True}
    return api_json(api, token, path + "/run", method="POST")


def health_flow(slug: str, api: str) -> dict:
    """A visible, hourly DBOS canary. Failures use Glacier's existing Home alerts."""
    command = (f"{python_command()} {shlex_quote(str(REPO / 'ventures/install_all.py').replace(chr(92), '/'))}"
               f" --health-canary {shlex_quote(slug)} --api {shlex_quote(api)}")
    return {"id": f"venture-health-{slug}", "name": f"{slug}: automation health",
            "nodes": [
                {"id": "hourly", "type": "schedule", "config": {
                    "cron": "5 * * * *", "missed_run": "run_once", "overlap": "skip"}},
                {"id": "health", "type": "command", "config": {
                    "cmd": command, "cwd": str(REPO), "timeout": 120, "retries": 0}},
                {"id": "report", "type": "note", "config": {
                    "path": f"ventures/{slug}/health/{{run}}.md",
                    "template": "Automation health (local runtime only, not a live source certification):\n\n{prev_output}"}}],
            "edges": [{"id": "h1", "source": "hourly", "target": "health"},
                      {"id": "h2", "source": "health", "target": "report"}]}


def health_canary(api: str, token: str, slug: str) -> dict:
    from dbos._croniter import croniter

    manifest = json.loads(manifests(slug, ready_only=True)[0].read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    rows = []
    problems = []
    for flow_id in manifest["flows"]:
        graph = api_json(api, token, f"/api/environments/{quote(flow_id, safe='')}")
        if graph.get("enabled") is False:
            rows.append({"flow": flow_id, "state": "paused by owner"})
            continue
        schedule = next((n for n in graph["nodes"] if n["type"] == "schedule"), None)
        if schedule is None:
            problems.append(f"{flow_id}: schedule missing; reinstall with --ready")
            continue
        runs = api_json(api, token, f"/api/runs?env_id={quote(flow_id, safe='')}")
        latest = max(runs, key=lambda r: r["started_at"], default=None)
        state = latest["status"] if latest else "not run yet"
        rows.append({"flow": flow_id, "state": state, "run_id": latest["run_id"] if latest else None})
        if not latest or state == "failed":
            problems.append(f"{flow_id}: {state}; open its run in Glacier")
        elif state not in ("waiting", "running", "queued"):
            started = datetime.fromisoformat(latest["started_at"].replace("Z", "+00:00"))
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            expected = croniter(schedule["config"]["cron"], started, second_at_beginning=True).get_next(datetime)
            if now > expected + timedelta(hours=2):
                problems.append(f"{flow_id}: scheduled run overdue since {expected.isoformat()}")
        elif state in ("running", "queued"):
            started = datetime.fromisoformat(latest["started_at"].replace("Z", "+00:00"))
            if now - started.replace(tzinfo=timezone.utc) > timedelta(hours=24):
                problems.append(f"{flow_id}: running or queued for more than 24 hours")
    return {"venture": slug, "checked_at": now.isoformat(), "scope": "local automation runtime",
            "flows": rows, "problems": problems, "healthy": not problems}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="install only this venture slug")
    parser.add_argument("--api", default=os.environ.get("GLACIER_API", "http://127.0.0.1:8000"))
    parser.add_argument("--dry-run", action="store_true", help="validate manifests and flows without contacting Glacier")
    parser.add_argument("--ready", action="store_true", help="install only ready ventures, with schedules and hourly health canaries")
    parser.add_argument("--start", action="store_true", help="also start each installed flow, preserving pauses and active owner waits")
    parser.add_argument("--prove", metavar="OUTPUT_DIR", type=Path,
                        help="run ready flows in a disposable real backend; record completions and owner stops")
    parser.add_argument("--health-canary", metavar="SLUG", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.prove:
            command = [sys.executable, str(ROOT / "job-closeout/flows/prove_automations.py"),
                       "--output", str(args.prove)]
            if args.only:
                command.extend(["--only", args.only])
            return subprocess.run(command, check=False).returncode
        if args.health_canary:
            result = health_canary(args.api, _engine_token(), args.health_canary)
            print(json.dumps(result, indent=2))
            return 0 if result["healthy"] else 1
        result = (validate_all(args.only, ready_only=args.ready) if args.dry_run else
                  install(args.api, _engine_token(), args.only, ready_only=args.ready, start=args.start))
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, HTTPError, URLError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        print(f"venture install failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
