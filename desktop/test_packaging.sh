#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

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
