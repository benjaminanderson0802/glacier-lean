# E-PH2 results

Implementation: `3cc7e8d` (2026-10-10 local date).

Changes: gateway defaults to granite3.3:2b. Invalid/empty model answers and invalid
usage are rejected before a gateway route records success; the next free route
can answer. Ollama invalid/empty responses return a failed worker result with a
plain-language error. Existing checks and acceptance files were not edited.

## Verified with fixtures

From glacier/backend, using `~/w/glacier-lean/.venv/bin/python`:

```
-m pytest -q tests/test_worker_reply_validation.py tests/test_gateway.py tests/test_gateway_preferred.py
```

28 passed (unit-after.log). The new ordinary unit regressions had 16 failures
and one pass before implementation (unit-before.log). These cover malformed
response fallback, correct usage, default Granite, preferred-route online/offline,
daily caps, and paid-route refusal. Preferred laptop behavior is simulated.

Current card-session rerun from `glacier/backend`:

```
~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_worker_reply_validation.py tests/test_gateway.py tests/test_gateway_preferred.py
```

28 passed in 5.50s. A broader focused run including local-AI and ACP tests reached
30 passed before it blocked during another backend fixture startup; Ctrl-C ended
that invocation (exit 2), so it is not a passing suite. A second isolated local
answer/ACP run reached 17 passed and blocked at backend startup; Ctrl-C ended it
(exit 2). Both startup stalls are recorded in the live-gaps claim. The failed
test-path typo before these runs collected no tests and is not acceptance evidence.

## Environment limits

`-m pytest -q tests/test_worker_reply_validation.py tests/test_local_ai.py --maxfail=1`
finished with 20 passed, 1 failed: the 404 local-model case could not start its
backend in 60 seconds, before it invoked the worker (focused.log).

The selected real-engine suite
`-m pytest -q tests/test_flows_real_runtime.py -k 'real_local_ai_waits or real_codex_worker or real_http_decide'`
finished with 1 failed, 2 skipped, 23 deselected. Ollama availability probes
failed; Codex login status exceeded its 10-second limit (live-engines.log).
Supplemental direct gateway calls against the real Ollama service also failed
to reach a model (live-gateway.json). They are not claimed as live success.

Full backend command was queued under `/tmp/glacier-suite.lock` for over 11
minutes without starting pytest. The queued launcher was cancelled, with no
running test or other worker stopped (backend-full.log).

## Screen checks

From glacier/web:

- `node e2e/theme_lint.mjs`: passed, 52 files (theme.log).
- `npx tsc -b`: missing project TypeScript; npx resolved the unrelated tsc package.
- `node scripts/check-i18n.mjs --fail`: missing typescript (i18n.log).
- `npm run build`: `tsc: not found` (web-build.log).
- `node e2e/live_real_backend.spec.mjs`: missing playwright (web-live.log).

No screen behavior or mock payload changed. Shared dependencies were not
installed or altered. The legacy core shell script would change shared
dependencies/delete a fixed temporary directory, and its Codex helper targets
port 8000 without an install token; neither was rewritten or run that way.

## Existing real-engine evidence

The subscription Codex worker has historical real-run evidence in
`evidence/live/acp_two_harnesses.md` (Codex ACP completed the same checked file
goal as the other harness, with both Glacier and independent checks passing) and
`evidence/live/portable_three_backends.md` (Codex CLI completed the coding goal;
its independent pytest check passed). These artifacts remain distinct from this
card-session run. Claude CLI is not installed here, and this session's Codex
login-status probe timed out; no new live subscription-engine success is claimed.

Local Granite is fixture-tested, but its real coding portability attempt in
`evidence/live/portable_three_backends.md` failed the independent check because
OpenCode described tool operations without creating the files. A direct gateway
probe could not reach Ollama (`live-gateway.json`).

## Remaining work

PH2 is not closed; no NORTHSTAR completion claim is made. PH2.2 is returned to
`in_progress`: fixture checks pass, but the specified real offline-model task has
not passed in this environment. Claude live proof requires its missing CLI and
owner authentication; real second-machine proof remains an owner hardware step.
The environment and board blockers are tracked in
CLM-2026-10-10-E-PH2-LIVE-GAPS. Anti-pattern review is in docs/AMENDMENTS.md.
