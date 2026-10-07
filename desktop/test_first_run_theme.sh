#!/usr/bin/env bash
# The desktop first-run page must use the exact Glacier theme (owner's rule: never a generic look).
set -euo pipefail
cd "$(dirname "$0")"
cmp -s first-run/theme/tokens.css ../glacier/web/src/theme/tokens.css || { echo "first-run/theme/tokens.css differs from glacier/web/src/theme/tokens.css; copy it again" >&2; exit 1; }
for f in ../glacier/web/src/theme/fonts/*.woff2; do cmp -s "$f" "first-run/theme/fonts/$(basename "$f")" || { echo "font $(basename "$f") differs" >&2; exit 1; }; done
if grep -nE '#[0-9a-fA-F]{3,8}\b|rgba?\(|system-ui|sans-serif|Arial|Inter|fonts\.googleapis' first-run/index.html first-run/app.js; then
  echo "first-run page defines its own colours or fonts; use the tokens" >&2; exit 1
fi
echo "first-run theme ok"
