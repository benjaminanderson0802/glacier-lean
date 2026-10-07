#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
bash test_first_run_theme.sh
(cd ../glacier/web && npm run build)
rm -rf dist
mkdir -p dist
cp -a ../glacier/web/dist/. dist/
cp -a first-run dist/first-run
test -f dist/first-run/index.html
# The bundled Python runtime is a release resource (package_linux.sh builds it). For this debug build check,
# create an empty placeholder when it is missing so the build does not need a download.
case "$(uname -s)" in
  Linux) rt=x86_64-unknown-linux-gnu ;; Darwin) rt=aarch64-apple-darwin ;; *) rt=x86_64-pc-windows-msvc ;;
esac
[[ -d "runtime/$rt" ]] || mkdir -p "runtime/$rt"
TAURI_APP_PATH=src-tauri TAURI_FRONTEND_PATH=. \
  npx tauri build --debug --no-bundle
binary="src-tauri/target/debug/glacier-desktop"
if [[ ! -x "$binary" ]]; then
  echo "Desktop build did not create executable: $binary" >&2
  exit 1
fi
grep -q 'low_resource' sidecar.json
grep -q 'codex' first-run/app.js
grep -q '"frontendDist": "../dist"' src-tauri/tauri.conf.json
echo "Desktop build check passed: $binary"
