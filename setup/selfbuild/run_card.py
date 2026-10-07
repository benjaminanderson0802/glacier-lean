#!/usr/bin/env python3
"""Load a card file into Glacier's feature flow and start the run through the local API."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import subprocess

import httpx

ROOT = Path(__file__).resolve().parents[2]
FLOW_PATH = ROOT / "flows" / "self" / "feature.json"
MAINTENANCE_PATH = ROOT / "flows" / "self" / "maintenance.json"
GUARD_PATH = ROOT / "setup" / "selfbuild" / "protected_guard.py"


def prepare_checkout(home: Path, source: Path) -> Path:
    """Create or verify the maintained Glacier checkout used by self-build runs."""
    target = home / "workspaces" / "self-feature"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not (target / ".git").exists():
        subprocess.run(["git", "clone", str(source), str(target)], check=True, capture_output=True, text=True)
    else:
        actual = Path(subprocess.check_output(["git", "-C", str(target), "rev-parse", "--show-toplevel"], text=True).strip())
        if actual.resolve() != target.resolve():
            raise RuntimeError(f"Self-build checkout path is not a Git repository: {target}")
        try:
            origin = subprocess.check_output(["git", "-C", str(target), "remote", "get-url", "origin"], text=True).strip()
        except subprocess.CalledProcessError:
            origin = ""
        if origin and Path(origin).exists() and Path(origin).resolve() != source.resolve():
            raise RuntimeError(f"Self-build checkout has unexpected origin: {origin}")
    dirty = subprocess.check_output(["git", "-C", str(target), "status", "--porcelain"], text=True).strip()
    if dirty:
        raise RuntimeError(f"Self-build checkout has uncommitted changes: {target}")
    current = subprocess.check_output(["git", "-C", str(target), "branch", "--show-current"], text=True).strip()
    if current != "main":
        has_main = subprocess.run(["git", "-C", str(target), "show-ref", "--verify", "--quiet", "refs/heads/main"]).returncode == 0
        has_origin_main = subprocess.run(["git", "-C", str(target), "show-ref", "--verify", "--quiet", "refs/remotes/origin/main"]).returncode == 0
        if has_main:
            command = ["git", "-C", str(target), "switch", "main"]
        elif has_origin_main:
            command = ["git", "-C", str(target), "switch", "--track", "-c", "main", "origin/main"]
        else:
            raise RuntimeError("Self-build checkout needs a local or origin main branch for verified merges")
        subprocess.run(command, check=True, capture_output=True, text=True)
    return target


def install_maintenance(client: httpx.Client, repo: Path) -> None:
    flow = json.loads(MAINTENANCE_PATH.read_text(encoding="utf-8"))
    for node in flow["nodes"]:
        config = node.get("config", {})
        if config.get("cwd") == "{repo}":
            config["cwd"] = str(repo)
    saved = client.put(f"/api/environments/{flow['id']}", json=flow)
    saved.raise_for_status()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start a Glacier self-build run from a card file.")
    parser.add_argument("card", help="Path to a text card file")
    parser.add_argument("--api", default=os.environ.get("GLACIER_API_URL", "http://127.0.0.1:8000"),
                        help="Glacier API base URL")
    parser.add_argument("--home", type=Path, default=Path(os.environ.get("GLACIER_HOME", ROOT / "data")),
                        help="Glacier data folder (default: GLACIER_HOME)")
    args = parser.parse_args(argv)
    card_path = Path(args.card).expanduser().resolve()
    try:
        card_text = card_path.read_text(encoding="utf-8")
    except OSError as error:
        parser.error(f"Could not read card file {card_path}: {error}")
    try:
        repo = prepare_checkout(args.home.expanduser().resolve(), ROOT)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"Could not prepare the self-build checkout: {error}", file=sys.stderr)
        return 1
    flow = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    flow["goal"] = f"Build feature from {card_path.name}: {card_text[:300]}"
    # Shell single-quote the card text so the command node can pass it as prior output.
    flow["nodes"][0]["config"]["cmd"] = "printf '%s' '" + card_text.replace("'", "'\\''") + "'"
    baseline = str(ROOT)
    guard = str(GUARD_PATH)
    for node in flow["nodes"]:
        config = node.get("config", {})
        if node.get("type") == "codex":
            config["prompt"] += f"\n\nApproved card text:\n{card_text}"
        if node.get("type") == "command":
            config["cmd"] = config.get("cmd", "").replace("{guard}", guard).replace("{baseline}", baseline)
    try:
        with httpx.Client(base_url=args.api.rstrip("/"), timeout=30) as client:
            install_maintenance(client, repo)
            saved = client.put(f"/api/environments/{flow['id']}", json=flow)
            saved.raise_for_status()
            started = client.post(f"/api/environments/{flow['id']}/run")
            started.raise_for_status()
    except (httpx.HTTPError, ValueError) as error:
        print(f"Could not start card run: {error}", file=sys.stderr)
        return 1
    run_id = started.json()["run_id"]
    print(f"Started run {run_id}.")
    print(f"Watch it at {args.api.rstrip('/')}/api/runs/{run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
