#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 PYTHON BACKEND_DIR" >&2
  echo "Use the Python runtime and backend directory from an extracted desktop install." >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
python_path="$1"
[[ "$python_path" == /* ]] || python_path="$PWD/$python_path"
backend_dir="$(realpath "$2")"
[[ -x "$python_path" ]] || { echo "Python runtime is not executable: $python_path" >&2; exit 2; }
[[ -f "$backend_dir/app.py" ]] || { echo "Backend app.py was not found: $backend_dir" >&2; exit 2; }

host_python="$(command -v python3 || command -v python || true)"
[[ -n "$host_python" ]] || { echo "A host Python is needed only for HTTP requests and port selection." >&2; exit 2; }
temporary="$(mktemp -d)"
cleanup() {
  if [[ -n "${backend_pid:-}" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
    wait "$backend_pid" 2>/dev/null || true
  fi
  rm -rf "$temporary"
}
trap cleanup EXIT

empty_path="$temporary/no-developer-tools"
home="$temporary/home"
mkdir -p "$empty_path" "$home/profile"
port="$("$host_python" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
base_url="http://127.0.0.1:$port"
backend_log="$temporary/backend.log"

(
  cd "$backend_dir"
  exec env -u GIT_PYTHON_GIT_EXECUTABLE PATH="$empty_path" HOME="$home/profile" GLACIER_HOME="$home/data" \
    "$python_path" -m uvicorn app:app --host 127.0.0.1 --port "$port"
) >"$backend_log" 2>&1 &
backend_pid=$!

ready=0
for _ in {1..120}; do
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    break
  fi
  if "$host_python" -c 'import sys,urllib.request; urllib.request.urlopen(sys.argv[1], timeout=1)' "$base_url/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.25
done

if [[ "$ready" != 1 ]]; then
  echo "FAIL: installed backend did not start with developer Git absent from PATH."
  if [[ -f "$backend_log" ]]; then
    cat "$backend_log"
  fi
  exit 1
fi

export GLACIER_TEST_URL="$base_url"
export GLACIER_TEST_HOME="$home/data"
"$host_python" <<'PY'
import json
import os
import urllib.request

base = os.environ["GLACIER_TEST_URL"]
token_path = os.path.join(os.environ["GLACIER_TEST_HOME"], ".engine-token")
with open(token_path, encoding="utf-8") as f:
    token = f.read().strip()

def request(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

note_path = "notes/c-ph8-clean-startup-check.md"
first = request("PUT", "/api/memory/note", {
    "path": note_path,
    "body": "# Startup check\n\nOriginal note version.\n",
    "author": "owner",
})
second = request("PUT", "/api/memory/note", {
    "path": note_path,
    "body": "# Startup check\n\nEdited note version.\n",
    "author": "owner",
})
request("POST", "/api/memory/undo", {"path": note_path, "commit": second["commit"]})
restored = request("GET", "/api/memory/note?path=" + note_path)
if "Original note version." not in restored["body"]:
    raise SystemExit("FAIL: undo did not restore the original saved note")
if "Edited note version." in restored["body"]:
    raise SystemExit("FAIL: edited note content remains after undo")
print("PASS: installed backend started, initialized its vault, committed two note saves, and undo restored the original note.")
print("Commits: first={}, edited={}, undo={}".format(first["commit"], second["commit"], "recorded"))
PY
