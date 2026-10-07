#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Linux packages must be built on Linux." >&2
  exit 1
fi

missing=()
for package in libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev librsvg2-dev patchelf; do
  dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed' || missing+=("$package")
done
if ((${#missing[@]})); then
  echo "Missing Linux build packages: ${missing[*]}" >&2
  echo "Install them with: sudo apt-get update && sudo apt-get install -y ${missing[*]}" >&2
  exit 1
fi

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "Warning: Python 3.12 is not installed. The packages include backend source but require Python 3.12 at runtime." >&2
fi

npx tauri build --bundles deb,appimage

echo "Linux packages created:"
find src-tauri/target/release/bundle/deb src-tauri/target/release/bundle/appimage \
  -maxdepth 1 -type f \( -name '*.deb' -o -name '*.AppImage' \) -printf '%p (%s bytes)\n' | sort
