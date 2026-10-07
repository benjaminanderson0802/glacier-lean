#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 - <<'PY'
import json
from pathlib import Path

sidecar = json.loads(Path("sidecar.json").read_text(encoding="utf-8"))
script = Path("scripts/smoke_windows.ps1").read_text(encoding="utf-8")
unix_script = Path("scripts/smoke_unix.sh").read_text(encoding="utf-8")
lib_rs = Path("src-tauri/src/lib.rs").read_text(encoding="utf-8")
runtime = sidecar["runtime_by_platform"]["x86_64-pc-windows-msvc"]
args = ['"-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "$port"']
lib_args = '.args(["-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", &port_text])'
required = [
    runtime.replace("/", "\\"),
    *args,
    '$env:GLACIER_HOME = $dataDir',
]
missing = [value for value in required if value not in script]
if lib_args not in lib_rs:
    missing.append("lib.rs backend argument list")
for key, value in sidecar["low_resource_env"].items():
    if f'$env:{key} = "{value}"' not in script:
        missing.append(f"sidecar low-resource setting {key}")
if missing:
    raise SystemExit("Windows smoke script does not match sidecar/lib.rs startup settings: " + ", ".join(missing))
print("Windows smoke startup arguments match sidecar.json and lib.rs")

unix_args = 'backend_args=(-m uvicorn app:app --host 127.0.0.1 --port "$port")'
unix_required = [
    unix_args,
    '"$python_path" "${backend_args[@]}"',
    'cd "$backend_dir"',
    'export GLACIER_HOME="$data_dir"',
]
missing_unix = [value for value in unix_required if value not in unix_script]
if lib_args not in lib_rs:
    missing_unix.append("lib.rs backend argument list")
if 'runtime_relative="runtime/$platform/bin/python3.12"' not in unix_script:
    missing_unix.append("sidecar Unix runtime path")
for key, value in sidecar["low_resource_env"].items():
    if f'export {key}="{value}"' not in unix_script:
        missing_unix.append(f"sidecar low-resource setting {key}")
if missing_unix:
    raise SystemExit("Unix smoke script does not match sidecar.json and lib.rs startup settings: " + ", ".join(missing_unix))
print("Unix smoke startup arguments match sidecar.json and lib.rs")
PY

bundle_dir="src-tauri/target/release/bundle"
deb="$(find "$bundle_dir/deb" -maxdepth 1 -type f -name '*.deb' -print -quit 2>/dev/null || true)"
appimage="$(find "$bundle_dir/appimage" -maxdepth 1 -type f -name '*.AppImage' -print -quit 2>/dev/null || true)"

if [[ -z "$deb" ]]; then
  echo "Deb check skipped: build a .deb first with ./package_linux.sh"
else
  contents="$(dpkg-deb --contents "$deb")"
  for resource in backend/app.py backend/requirements.txt backend/nodes/ backend/routes/ contract/node_types.json; do
    if ! grep -Fq "$resource" <<<"$contents"; then
      echo "Deb package is missing backend resource: $resource" >&2
      exit 1
    fi
  done
  if ! grep -Fq 'runtime/x86_64-unknown-linux-gnu/bin/python3.12' <<<"$contents"; then
    echo "Deb package is missing the bundled Linux Python runtime" >&2
    exit 1
  fi
  runtime_dir="$(mktemp -d)"
  trap 'rm -rf "$runtime_dir"' EXIT
  dpkg-deb -x "$deb" "$runtime_dir"
  python_path="$(find "$runtime_dir" -path '*/runtime/x86_64-unknown-linux-gnu/bin/python3.12' -type f -print -quit)"
  if [[ -z "$python_path" ]]; then
    echo "Could not locate bundled Python in extracted .deb" >&2
    exit 1
  fi
  "$python_path" -c 'import fastapi, dbos'
  echo "Extracted bundled runtime imports fastapi and dbos"
  echo "Deb contains backend source and contract resources: $deb"
fi

if [[ -z "$appimage" ]]; then
  echo "AppImage check skipped: build an AppImage first with ./package_linux.sh"
elif command -v xvfb-run >/dev/null 2>&1 && command -v xauth >/dev/null 2>&1; then
  if timeout 20 xvfb-run -a "$appimage" --help >/dev/null 2>&1; then
    echo "AppImage --help exited cleanly under xvfb: $appimage"
  else
    status=$?
    echo "AppImage headless launch failed (exit $status): $appimage" >&2
    exit "$status"
  fi
else
  echo "AppImage launch check skipped: xvfb-run or xauth is unavailable"
fi
