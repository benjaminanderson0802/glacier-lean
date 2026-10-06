#!/usr/bin/env bash
# Installs the Glacier core at pinned versions and runs every core test. Log: /tmp/run_core.log
set -x
cd "$(dirname "$0")/.."
uv pip install --quiet --python .venv/bin/python -r setup/requirements.txt
cd glacier/web && npm ci --no-audit --no-fund --loglevel=error && npx tsc -b && npx vite build > /dev/null && cd ../backend
../../.venv/bin/python -m pytest tests -q 2>&1 | tail -3
rm -rf /tmp/e2edata
GLACIER_HOME=/tmp/e2edata nohup ../../.venv/bin/python -m uvicorn app:app --port 8000 > /tmp/backend.log 2>&1 &
sleep 6
cd ../web && SKIP_MOCK=1 API_URL=http://localhost:8000 node e2e/core.spec.mjs 2>&1 | grep -aE '\[e2e\]|^PASS|^FAIL'
echo CORE_DONE
