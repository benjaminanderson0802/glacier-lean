# E-PH6 backend work, 2026-10-10

## Drift check and acceptance plan (before implementation)

1. Owner-assigned card E-PH6 advances PH6.1 (export imports), PH6.2 (local
   session mirroring), and verifies backend portions of PH6.3 (files, images,
   projects, search and rename). The roadmap already marks all four building
   checkpoints done; the current audit identifies incomplete live proof.
2. PH2 and PH5 are recorded in progress, not at phase exit. The owner's explicit
   parallel-safe card authorizes this work; no dependency or phase exit is changed.
3. P-USABLE, P-MEMORY, P-PORTABLE; M-TTFA and M-PORTABLE. Correct import audit
   counts additionally serve P-CONTROL and M-AUDIT. No user timing metric is
   claimed from these backend checks.
4. Reuse the existing stdlib JSONL readers, importers, FastAPI routes, vault/git,
   and optional Tesseract integration. Changes are product glue; no dependency,
   license, service, paid route, or consumer-login integration is added.
5. Existing acceptance: unchanged test_session_mirror*.py, test_import_service.py,
   test_files.py, test_image_files.py and test_memory_rename.py. Existing document,
   fetch and search checks remain on the backend board. New ordinary unit tests
   reproduce the lost-title and zero-write-count bugs before their fixes.

## Changes

- `a027c0b`: retain the first meaningful user title when older events roll out
  of the 2,000-event preview. Session lists no longer format commands and output
  they do not return. Full transcript reads, redaction and source files are unchanged.
- `c23f0ea`: import/refresh audit events count added plus updated notes; unchanged
  notes do not count as writes. Both multipart and local-path imports use the fix.

No existing test, acceptance file, API response shape, screen, mock, data-testid,
NORTHSTAR field or phase exit was changed. Re-read the anti-pattern list: this
card contains user-visible fixes and preserves incomplete verification as claims,
without adding a custom orchestration layer or declaring the phase complete.

## Commands and evidence

All Python commands use `~/w/glacier-lean/.venv/bin/python`; pytest runs from
`glacier/backend`. Logs are in this folder.

- Baseline: `-m pytest -q tests/test_session_mirror.py tests/test_session_mirror_more.py
  tests/test_session_mirror_opencode.py tests/test_import_service.py tests/test_files.py
  tests/test_image_files.py tests/test_memory_rename.py`: **69 passed, 1 startup
  error**, before changes (`baseline-tests.log`). The error is a 60-second backend
  fixture startup timeout, not an assertion failure.
- New title units before fix: **1 failed, 1 passed** (`title-reproduction.log`).
- New audit units before fix: **3 failed** (`import-audit-reproduction.log`).
- Focused PH6 backend board (`test_session_summary_units.py`, the Codex and
  OpenCode mirror tests, chat titles, import audit/service, files, images and
  memory rename): **80 passed** (`session-tests.log`).
- Full backend board was not rerun: the shared suite lock was occupied by
  other workers' backend runs. No other worker process was stopped. The focused
  suites for both changed behaviors passed above.
- From `glacier/web`: `node e2e/theme_lint.mjs`: **passed, 52 files**.
  `npx tsc -b`, `node scripts/check-i18n.mjs --fail`, and `npm run build`:
  **blocked by missing shared TypeScript dependency**. The existing
  `node e2e/shell.spec.mjs` and `node e2e/live_real_backend.spec.mjs` also fail to
  load because Playwright is absent. Logs preserve every result.

The legacy core script mutates a shared dependency directory, deletes a fixed
temporary home and starts a fixed-port backend; its live Codex companion omits
the required authentication. They were not run against other workers' processes.
The locked backend board and isolated real-backend API walkthrough were used
instead; see the shared-verification claim for the script-owner follow-up.

## Live versus fixture evidence

`live-api.json` / `live-api.log` record an actual uvicorn server in a new temporary
GLACIER_HOME with authentication enabled. Only that server process is stopped.
Disposable ChatGPT/Claude export-format examples are uploaded over HTTP,
deduplicated, refreshed and searched. Text and PNG files are uploaded into a
project; the resulting text note is renamed and found at its new path. Session
listing reads the real local corpus, but evidence stores only counts and timing,
not private session contents.

The walkthrough completed successfully. The real audit database records writes
`1, 0, 1, 0, 0` for first ChatGPT import, repeat, first Claude import, repeat,
and unchanged refresh. Cold HTTP discovery returned 875 sessions (827 Codex,
48 OpenCode) in 126.367 seconds; warm discovery returned 876 in 0.061 seconds.
The corpus grew while other workers were active. This does not close the cold
latency gap.

This is live backend proof with synthetic export/file inputs, not proof of an
actual ChatGPT account export or a browser walkthrough. Tesseract is absent:
image storage plus the installation hint work live; OCR behavior is covered by
the existing fake-Tesseract tests, not a real OCR execution. Other harness
transcript formats are covered by the existing fixtures, not new live harness runs.

## Outstanding

- Cold session discovery remains above the audit's five-second request target:
  `CLM-2026-10-10-E-PH6-COLD-SESSION-LIST`. The shared-load timings cannot support
  a performance improvement claim, although warm discovery is fast.
- Shared environment/startup and web dependencies:
  `CLM-2026-10-10-E-PH6-SHARED-VERIFICATION`.
- PH6's two-week primary-workspace exit requires the owner's attestation and
  matching usage log. This backend card cannot supply that owner-only evidence.
