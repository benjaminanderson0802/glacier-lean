"""Validate and install manifest-listed venture flows into local Glacier."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
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


def manifests(only: str | None = None) -> list[Path]:
    found = sorted(ROOT.glob("*/venture.json"))
    if only:
        found = [path for path in found if json.loads(path.read_text(encoding="utf-8")).get("slug") == only]
        if not found:
            raise ValueError(f"venture manifest not found: {only}")
    if not found:
        raise ValueError("no venture manifests found; no flows can be installed")
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


def validate_all(only: str | None = None) -> list[dict]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    known_types = _catalog_types()
    checked: list[dict] = []
    slugs: set[str] = set()
    for manifest_path in manifests(only):
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
    python = shlex_quote(sys.executable)
    import_path = f"{repo_root}:{venture_cwd}"

    def bind_command(command: str) -> str:
        command = command.replace("{python}", python)
        command = command.replace("PYTHONPATH=. .venv/bin/python", f"PYTHONPATH={shlex_quote(import_path)} {python}")
        command = re.sub(r"(?<![A-Za-z0-9_./-])python3?(?=\s)", python, command)
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
            config["cmd"] = f"PYTHONPATH={shlex_quote(import_path)}${{PYTHONPATH:+:$PYTHONPATH}} {bind_command(command)}"
    for key in ("acceptance", "checks"):
        rows = result.get(key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and isinstance(row.get("cmd"), str):
                    row["cmd"] = bind_command(row["cmd"])
    return result


def python_command() -> str:
    """Compatibility helper returning the interpreter used for installed flows."""
    return shlex_quote(sys.executable)


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
        if current == flow:
            return {"saved": False, "unchanged": True}
    return register_flow(api, token, flow)


def install_flow(flow: dict, *, base: str, token: str) -> dict:
    """Compatibility helper for registering a single flow through idempotent PUT."""
    api = base[:-4] if base.endswith("/api") else base
    return register_flow(api, token, flow)


def install(api: str, token: str, only: str | None = None, *, home: Path | None = None) -> list[dict]:
    validate_all(only)
    data_home = home or Path(os.environ.get("GLACIER_HOME", "data"))
    registered: list[dict] = []
    for manifest_path in manifests(only):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        slug = manifest["slug"]
        flow_ids = manifest["flows"]
        _stage_scripts(manifest_path.parent, slug, data_home, flow_ids)
        for flow_id in flow_ids:
            flow_path = flow_file(manifest_path, flow_id)
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            runtime = _runtime_flow(flow, repo_root=REPO, slug=slug, home=data_home)
            result = register_flow_if_changed(api, token, runtime)
            registered.append({"venture": slug, "flow": flow_id, "result": result})
    return registered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="install only this venture slug")
    parser.add_argument("--api", default=os.environ.get("GLACIER_API", "http://127.0.0.1:8000"))
    parser.add_argument("--dry-run", action="store_true", help="validate manifests and flows without contacting Glacier")
    args = parser.parse_args()
    try:
        result = validate_all(args.only) if args.dry_run else install(args.api, _engine_token(), args.only)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, HTTPError, URLError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        print(f"venture install failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
