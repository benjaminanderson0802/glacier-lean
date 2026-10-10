"""Idempotently register manifest-listed venture flows with a local Glacier."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent


def manifests(only: str | None = None) -> list[Path]:
    found = sorted(ROOT.glob("*/venture.json"))
    if only:
        found = [path for path in found if json.loads(path.read_text(encoding="utf-8")).get("slug") == only]
        if not found:
            raise ValueError(f"venture slug not found: {only}")
    return found


def engine_token() -> str:
    home = Path(os.environ.get("GLACIER_HOME", "data"))
    token_path = home / ".engine-token"
    if not token_path.is_file():
        raise FileNotFoundError(f"Glacier engine token not found: {token_path}")
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"Glacier engine token is empty: {token_path}")
    return token


def _runtime_flow(flow: dict, *, repo_root: Path, slug: str, home: Path) -> dict:
    """Point flow commands at a staged copy and make shared packages importable."""
    result = json.loads(json.dumps(flow))
    workspace = home / "workspaces" / str(flow["id"])
    venture_cwd = workspace / "ventures" / slug
    for node in result.get("nodes", []):
        if node.get("type") != "command":
            continue
        config = node.setdefault("config", {})
        requested = str(config.get("cwd") or "").strip()
        if requested == f"ventures/{slug}":
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


def shlex_quote(value: str) -> str:
    # Quote one trusted local path for the command shell used by Glacier.
    return "'" + value.replace("'", "'\"'\"'") + "'"


def register_flow(api: str, token: str, flow: dict) -> dict:
    flow_id = flow.get("id")
    if not flow_id or not isinstance(flow.get("nodes"), list) or not isinstance(flow.get("edges"), list):
        raise ValueError("flow file must include id, nodes, and edges")
    payload = json.dumps(flow).encode("utf-8")
    request = Request(
        f"{api.rstrip('/')}/api/environments/{quote(str(flow_id), safe='')}",
        data=payload,
        method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_schedules(manifest: dict, flow: dict) -> None:
    flow_id = flow.get("id")
    declared = [row for row in manifest.get("schedules", []) if row.get("flow") == flow_id]
    schedule_nodes = [node for node in flow.get("nodes", []) if node.get("type") == "schedule"]
    if len(declared) != len(schedule_nodes):
        raise ValueError(f"{flow_id}: manifest schedule entries do not match schedule nodes")
    for row, node in zip(declared, schedule_nodes):
        if row.get("cron") != node.get("config", {}).get("cron"):
            raise ValueError(f"{flow_id}: manifest cron does not match schedule node")


def install(api: str, token: str, only: str | None = None, *, home: Path | None = None) -> list[dict]:
    registered: list[dict] = []
    data_home = home or Path(os.environ.get("GLACIER_HOME", "data"))
    repo_root = ROOT.parent
    for manifest_path in manifests(only):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        slug = manifest.get("slug")
        venture_dir = manifest_path.parent
        flow_ids = manifest.get("flows", [])
        _stage_scripts(venture_dir, slug, data_home, flow_ids)
        for flow_id in flow_ids:
            flow_path = venture_dir / "flows" / f"{flow_id}.json"
            if not flow_path.is_file():
                raise FileNotFoundError(f"{slug}: flow declared by manifest is missing: {flow_path}")
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            if flow.get("id") != flow_id:
                raise ValueError(f"{flow_path}: id does not match manifest flow {flow_id}")
            validate_schedules(manifest, flow)
            result = register_flow(api, token, _runtime_flow(flow, repo_root=repo_root, slug=slug, home=data_home))
            registered.append({"venture": slug, "flow": flow_id, "result": result})
    return registered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="install only a venture slug")
    parser.add_argument("--api", default=os.environ.get("GLACIER_API", "http://127.0.0.1:8000"))
    parser.add_argument("--dry-run", action="store_true", help="validate manifests and flows without contacting Glacier")
    args = parser.parse_args()
    try:
        if args.dry_run:
            output = []
            for manifest_path in manifests(args.only):
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                for flow_id in manifest.get("flows", []):
                    flow = json.loads((manifest_path.parent / "flows" / f"{flow_id}.json").read_text(encoding="utf-8"))
                    if flow.get("id") != flow_id:
                        raise ValueError(f"flow id mismatch for {flow_id}")
                    validate_schedules(manifest, flow)
                    output.append({"venture": manifest["slug"], "flow": flow_id, "validated": True})
        else:
            output = install(args.api, engine_token(), args.only)
        print(json.dumps(output, indent=2))
        return 0
    except (OSError, ValueError, HTTPError, URLError, json.JSONDecodeError) as exc:
        print(f"venture install failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
