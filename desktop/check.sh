#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
(cd ../glacier/web && npm run build)
TAURI_APP_PATH=src-tauri TAURI_FRONTEND_PATH=. \
  npx tauri build --debug --no-bundle
binary="src-tauri/target/debug/glacier-desktop"
if [[ ! -x "$binary" ]]; then
  echo "Desktop build did not create executable: $binary" >&2
  exit 1
fi
grep -q 'low_resource' sidecar.json
grep -q 'codex' first-run/index.html
echo "Desktop build check passed: $binary"
