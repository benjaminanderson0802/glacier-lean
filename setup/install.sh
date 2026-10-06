#!/usr/bin/env bash
# Installs Glacier's basic foundation at pinned versions. No AI models, no API keys.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || pip install --quiet uv
uv venv --quiet .venv
uv pip install --quiet --python .venv/bin/python -r setup/requirements.txt
git config --global user.email >/dev/null || git config --global user.email "glacier@localhost"
git config --global user.name  >/dev/null || git config --global user.name  "glacier"
cd tests/ui && npm install --no-audit --no-fund --loglevel=error && npx playwright install --with-deps chromium >/dev/null
echo "Install complete. Run: .venv/bin/python tests/run_all.py"
