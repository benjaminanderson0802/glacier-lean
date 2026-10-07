#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --appimage FILE | --deb FILE | --app APP_BUNDLE" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
kind="$1"
artifact="$2"
[[ -e "$artifact" ]] || { echo "Unix desktop smoke test failed: artifact was not found: $artifact" >&2; exit 1; }
artifact="$(cd "$(dirname "$artifact")" && pwd)/$(basename "$artifact")"

temporary="$(mktemp -d)"
backend_pid=""
cleanup() {
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
    wait "$backend_pid" 2>/dev/null || true
  fi
  rm -rf "$temporary"
}
trap cleanup EXIT

case "$kind" in
  --appimage)
    chmod +x "$artifact"
    (cd "$temporary" && "$artifact" --appimage-extract >/dev/null)
    extracted="$temporary/squashfs-root"
    platform="x86_64-unknown-linux-gnu"
    ;;
  --deb)
    dpkg-deb -x "$artifact" "$temporary/deb"
    extracted="$temporary/deb"
    platform="x86_64-unknown-linux-gnu"
    ;;
  --app)
    extracted="$artifact/Contents/Resources"
    platform="aarch64-apple-darwin"
    ;;
  *) usage ;;
esac

runtime_relative="runtime/$platform/bin/python3.12"
python_path="$(find "$extracted" -type f -path "*/$runtime_relative" -print -quit)"
backend_dir="$(find "$extracted" -type f -path '*/backend/app.py' -print -quit | sed 's#/app.py$##')"
if [[ -z "$python_path" || -z "$backend_dir" ]]; then
  echo "Unix desktop smoke test failed: bundled Python or backend was not found in $artifact" >&2
  exit 1
fi

data_dir="$temporary/app-data"
mkdir -p "$data_dir"
export GLACIER_HOME="$data_dir"
# Match desktop/src-tauri/src/lib.rs and sidecar.json: backend cwd, Python arguments,
# app-data location, and low-resource environment are the same as the packaged app.
export GLACIER_LOCAL_MODEL="qwen3:0.6b"
export GLACIER_MAX_PARALLEL_RUNS="1"

listener_python="$(command -v python3 || command -v python)"
port="$("$listener_python" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
base_url="http://127.0.0.1:$port"
backend_log="$data_dir/backend.log"
backend_args=(-m uvicorn app:app --host 127.0.0.1 --port "$port")
(cd "$backend_dir" && exec "$python_path" "${backend_args[@]}" >"$backend_log" 2>&1) &
backend_pid=$!

fail() {
  echo "Unix desktop smoke test failed: $1" >&2
  if ! kill -0 "$backend_pid" 2>/dev/null && [[ -f "$backend_log" ]]; then
    echo "--- backend.log (last 40 lines) ---" >&2
    tail -n 40 "$backend_log" >&2
  fi
  exit 1
}

ready=0
deadline=$((SECONDS + 60))
while (( SECONDS < deadline )); do
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    fail "the bundled backend stopped during startup"
  fi
  if curl --silent --show-error --fail --max-time 2 "$base_url/api/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done
(( ready == 1 )) || fail "GET /api/health did not succeed within 60 seconds"

status="$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 10 "$base_url/api/system/settings" || true)"
[[ "$status" == "401" ]] || fail "an API request without the engine token returned $status, expected 401"
token_path="$data_dir/.engine-token"
for _ in {1..50}; do [[ -s "$token_path" ]] && break; sleep 0.2; done
[[ -s "$token_path" ]] || fail "the backend did not create its engine token"
token="$(cat "$token_path")"
status="$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 10 \
  -H "Authorization: Bearer $token" "$base_url/api/system/settings" || true)"
[[ "$status" == "200" ]] || fail "the token-authenticated API request returned $status, expected 200"

echo "Unix desktop smoke test passed: $kind backend readiness and token checks succeeded."
