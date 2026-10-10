#!/usr/bin/env python3
"""Idempotently register venture flows in a running Glacier instance."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VENTURES_DIR = Path(__file__).resolve().parent
REPO_ROOT = VENTURES_DIR.parent


def python_command() -> str:
    """Return a quoted invocation of the interpreter running the installer."""
    if os.name == "nt":
        return subprocess.list2cmdline([sys.executable])
    return shlex.quote(sys.executable)


def discover_flows(only: str | None = None) -> list[tuple[str, dict[str, object]]]:
    records: list[tuple[str, dict[str, object]]] = []
    seen_ids: set[str] = set()
    for manifest_path in sorted(VENTURES_DIR.glob("*/venture.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        slug = str(manifest.get("slug", manifest_path.parent.name))
        if only and slug != only:
            continue
        for relpath in manifest.get("flows", []):
            flow_path = manifest_path.parent / str(relpath)
            flow = json.loads(flow_path.read_text(encoding="utf-8"))
            for node in flow.get("nodes", []):
                config = node.get("config", {})
                if config.get("cwd") == "{repo}":
                    config["cwd"] = str(REPO_ROOT)
                command = config.get("cmd")
                if isinstance(command, str):
                    config["cmd"] = command.replace("{python}", python_command())
            for check in flow.get("acceptance", []):
                command = check.get("cmd")
                if isinstance(command, str):
                    check["cmd"] = command.replace("{python}", python_command())
            flow_id = str(flow.get("id", ""))
            if not flow_id:
                raise ValueError(f"Flow has no id: {flow_path}")
            if flow_id in seen_ids:
                raise ValueError(f"Duplicate flow id in venture manifests: {flow_id}")
            seen_ids.add(flow_id)
            records.append((slug, flow))
    if only and not records:
        raise ValueError(f"No venture flows found for slug: {only}")
    return records


def engine_token() -> str:
    home = Path(os.environ.get("GLACIER_HOME", Path.home() / ".glacier"))
    token_path = home / ".engine-token"
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"Glacier engine token is empty: {token_path}")
    return token


def api_base() -> str:
    base = os.environ.get("GLACIER_API", "http://localhost:8000/api").rstrip("/")
    return base if base.endswith("/api") else f"{base}/api"


def install_flow(flow: dict[str, object], *, base: str, token: str) -> dict[str, object]:
    flow_id = str(flow["id"])
    body = json.dumps(flow).encode("utf-8")
    request = Request(
        f"{base}/environments/{flow_id}",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not install Glacier flow {flow_id}: {exc}") from exc
    if not isinstance(result, dict) or result.get("saved") is not True:
        raise RuntimeError(f"Glacier did not confirm flow registration: {flow_id}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="Register only one venture slug")
    parser.add_argument("--dry-run", action="store_true", help="Print flow payloads without calling Glacier")
    args = parser.parse_args(argv)

    try:
        flows = discover_flows(args.only)
        token = "<from GLACIER_HOME/.engine-token>" if args.dry_run else engine_token()
        base = api_base()
        for slug, flow in flows:
            flow_id = flow["id"]
            if args.dry_run:
                print(json.dumps({"venture": slug, "url": f"{base}/environments/{flow_id}", "flow": flow}, indent=2))
            else:
                result = install_flow(flow, base=base, token=token)
                print(f"installed {slug}/{flow_id}: {result.get('commit', 'saved')}")
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
