#!/usr/bin/env bash
# Frees ports 8000/4173, runs the browser test against a fresh backend (fake Codex), then starts the live backend + screen.
cd /workspaces/glacier-lean/glacier/backend
for port in 8000 4173; do
  for pid in $(ss -ltnp 2>/dev/null | grep ":$port " | grep -oE 'pid=[0-9]+' | cut -d= -f2); do kill -9 "$pid"; done
done
sleep 1
rm -rf /tmp/e2e2
GLACIER_HOME=/tmp/e2e2 CODEX_BIN="$PWD/tests/fake_codex.py" ../../.venv/bin/python -m uvicorn app:app --port 8000 > /tmp/b2.log 2>&1 &
BP=$!
sleep 6
cd ../web && SKIP_MOCK=1 API_URL=http://localhost:8000 node e2e/core.spec.mjs 2>&1 | grep -aE 'codex|^PASS|^FAIL|ERROR'
kill -9 $BP; sleep 1
cd ../backend && GLACIER_HOME=/workspaces/glacier-data GLACIER_CODEX_SANDBOX=danger-full-access nohup ../../.venv/bin/python -m uvicorn app:app --port 8000 > /tmp/backend-live.log 2>&1 &
cd ../web && nohup npx vite preview --port 4173 --host 0.0.0.0 > /tmp/preview.log 2>&1 &
sleep 5
curl -s -o /dev/null -w 'live screen %{http_code}\n' localhost:4173
echo E2E2_DONE
