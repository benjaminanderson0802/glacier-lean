#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${PYTHON:-/workspaces/glacier-lean/.venv/bin/python}"
BACKEND="$ROOT/glacier/backend"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

for preset in codex-acp opencode; do
  workdir="$TMP/$preset"
  mkdir -p "$workdir"
  case "$preset" in
    codex-acp) command -v codex-acp >/dev/null || { echo "Blocked: codex-acp is not installed" >&2; exit 2; };;
    opencode) command -v opencode >/dev/null || { echo "Blocked: opencode is not installed" >&2; exit 2; };;
  esac
  PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" - "$ROOT" "$preset" "$workdir" <<'PY'
import json, os, sys, time, urllib.request
root, preset, workdir = sys.argv[1:]
base = os.environ.get("GLACIER_URL", "http://127.0.0.1:8421")
payload = {"id": "same-goal-" + preset, "name": "Same hello goal", "nodes": [
    {"id": "agent", "type": "acp_agent", "config": {"harness": preset,
     "prompt": "Create hello.txt containing exactly hi", "workdir": workdir, "timeout": 180}},
], "edges": []}
request = urllib.request.Request(base + "/api/environments/" + payload["id"], data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"}, method="PUT")
with urllib.request.urlopen(request) as response: response.read()
request = urllib.request.Request(base + "/api/environments/" + payload["id"] + "/run", data=b"{}",
                                headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(request) as response: run_id = json.load(response)["run_id"]
while True:
    with urllib.request.urlopen(base + "/api/runs/" + run_id) as response: run = json.load(response)
    if run.get("status") in {"done", "failed", "cancelled"}: break
    time.sleep(1)
if run.get("status") != "done": raise SystemExit(f"{preset}: run {run.get('status')}: {run.get('outputs')}")
PY
  test "$(cat "$workdir/hello.txt")" = "hi" || { echo "${preset}: hello.txt acceptance check failed" >&2; exit 1; }
  echo "${preset}: PASS — hello.txt contains hi"
done
