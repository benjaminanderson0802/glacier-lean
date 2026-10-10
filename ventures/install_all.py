"""Validate and install all venture flows into the local Glacier runtime."""
from __future__ import annotations

import argparse
import json
import os
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


@lru_cache(maxsize=1)
def _catalog_types() -> set[str]:
    catalog = json.loads(NODE_TYPES_PATH.read_text(encoding="utf-8"))
    core_types = {entry["type"] for entry in catalog["types"]}
    backend = str(REPO / "glacier" / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    import plugins

    plugin_types = {entry["type"] for entry in plugins.load_nodes(core_types)}
    return core_types | plugin_types


def validate_all(only: str | None = None) -> list[dict]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    known_types = _catalog_types()
    paths = sorted(ROOT.glob("*/venture.json"))
    if only:
        paths = [path for path in paths if path.parent.name == only]
        if not paths:
            raise ValueError(f"venture manifest not found: {only}")
    if not paths:
        raise ValueError("no venture manifests found; no flows can be installed")

    checked: list[dict] = []
    slugs: set[str] = set()
    for manifest_path in paths:
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
            schedule_nodes = [node for node in flow["nodes"] if node.get("type") == "schedule"]
            schedules = [row for row in declared_schedules if row.get("flow") == flow_id]
            if len(schedules) != len(schedule_nodes):
                raise ValueError(f"{flow_id}: manifest schedule entries do not match schedule nodes")
            for row, node in zip(schedules, schedule_nodes):
                if row["cron"] != node.get("config", {}).get("cron"):
                    raise ValueError(f"{flow_id}: manifest cron does not match schedule node")
            checked.append({"venture": slug, "flow": flow_id, "validated": True})
        if any(row.get("flow") not in declared_flows for row in declared_schedules):
            raise ValueError(f"{slug}: schedule references an undeclared flow")
    return checked


def _engine_token() -> str:
    home = Path(os.environ.get("GLACIER_HOME", "data"))
    token_path = home / ".engine-token"
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"Glacier engine token is empty: {token_path}")
    return token


def install(api: str, token: str, only: str | None = None) -> list[dict]:
    validate_all(only)
    results = []
    manifests = sorted(ROOT.glob("*/venture.json"))
    if only:
        manifests = [path for path in manifests if path.parent.name == only]
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for flow_id in manifest["flows"]:
            flow_path = manifest_path.parent / "flows" / f"{flow_id}.json"
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            request = Request(
                f"{api.rstrip('/')}/api/environments/{quote(flow_id, safe='')}",
                data=json.dumps(flow).encode("utf-8"), method="PUT",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            with urlopen(request, timeout=30) as response:
                results.append({"venture": manifest["slug"], "flow": flow_id,
                                "result": json.loads(response.read().decode("utf-8"))})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="install only this venture directory")
    parser.add_argument("--api", default=os.environ.get("GLACIER_API", "http://127.0.0.1:8000"))
    parser.add_argument("--dry-run", action="store_true", help="validate flows without contacting Glacier")
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
