"""Validate and install manifest-listed venture flows into local Glacier."""
from __future__ import annotations

import argparse
import json
import os
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
        if row["cron"] != node.get("config", {}).get("cron"):
            raise ValueError(f"{flow_id}: manifest cron does not match schedule node")


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
            flow_path = manifest_path.parent / "flows" / f"{flow_id}.json"
            if not flow_path.is_file():
                raise FileNotFoundError(f"{slug}: manifest flow is missing: {flow_path}")
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            if flow.get("id") != flow_id:
                raise ValueError(f"{flow_path}: id does not match manifest flow {flow_id}")
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
    """Point commands at a staged copy and make shared venture packages importable."""
    result = json.loads(json.dumps(flow))
    workspace = home / "workspaces" / str(flow["id"])
    venture_cwd = workspace / "ventures" / slug
    for node in result.get("nodes", []):
        if node.get("type") != "command":
            continue
        config = node.setdefault("config", {})
        if str(config.get("cwd") or "").strip() == f"ventures/{slug}":
            config["cwd"] = str(venture_cwd)
        command = str(config.get("cmd") or "")
        if command.startswith("python3 "):
            config["cmd"] = f"PYTHONPATH={shlex_quote(str(repo_root))}${{PYTHONPATH:+:$PYTHONPATH}} {command}"
    return result


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
            flow_path = manifest_path.parent / "flows" / f"{flow_id}.json"
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            runtime = _runtime_flow(flow, repo_root=REPO, slug=slug, home=data_home)
            result = register_flow(api, token, runtime)
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
