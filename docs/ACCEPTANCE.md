# Acceptance checks

## PH2 exit: portable backend swap bench

Run `bench/portable/run_portable.py` from the repository root with `.venv/bin/python`. The runner builds one single-worker flow for Codex CLI, OpenCode ACP and local Ollama, runs the same goal in separate temporary workspaces, and records the actual flow diff after normalizing only the worker backend configuration and workspace path. It independently checks the requested project with pytest. If any backend misses the coding goal, it tries a simpler exact-file goal across all three and reports both results. Live measurements are committed in `evidence/live/portable_three_backends.md`.

The independent check runs from the project interpreter and does not consume the worker's completion message. A backend counts as verified only if Glacier reports its acceptance command passing and the independent check passes. The PH2 target is 3/3 verified, with the same normalized flow apart from the worker backend field.

## PH8 exit: clean machine to a working first automation

The Windows desktop CI job builds and silently installs the NSIS installer on a clean GitHub
runner, starts the bundled backend with a new temporary data folder, and checks that protected API
requests fail without the install token and succeed with it. The smoke then calls `GET /api/starter`
and inspects the bundled templates returned by `GET /api/templates`. It chooses an installable flow
whose steps use only the built-in schedule, command, check, and note types, contain no AI or network
step, and save a note. (The current starter proposal only exposes `requires_local_model`; that flag
does not mean a flow needs no other tool, so CI does not use it as a no-extra-requirements signal.)

CI applies the selected flow through `POST /api/starter/apply`, starts it through the environment
run API, waits up to 120 seconds, requires a `done` status, and checks that the run's note exists in
the install data folder. Failures report the run's explanation with the install token redacted. On
success the job prints and uploads an evidence block with installer and bundled Python versions,
template id, run id, status, elapsed seconds, and output path. The smoke uninstalls the app afterward.

The automation uses no model and makes no network calls. The check is an installer/API integration
check; it does not measure the moderated first-use metric M-TTFA.

## Existing desktop checks

- `./check.sh` builds the Tauri debug app and verifies the resulting executable exists.
- Rust unit test `detects_installed_tools` confirms the tool scan returns every supported tool name and marks a fake executable as present.
- Low-resource mode is configured in `sidecar.json` and sets `GLACIER_LOCAL_MODEL=granite3.3:2b` and `GLACIER_MAX_PARALLEL_RUNS=1` for the backend.
- The app starts the backend on loopback at an OS-assigned port, waits for `/api/node-types`, then opens the built Glacier screen with that port.
- First-run information is a bundled plain-language page; tool results are local and no setup-report endpoint is called.

## PH10 acceptance runner

Run the PH10 proof table from the repository root:

```sh
.venv/bin/python bench/ph10/run_ph10.py
```

The runner calls the existing guide/help link check, template manifest and safety tests, localization checker, screen test when available, and interoperability tests by pytest node ID. Its process exit is nonzero when any check fails. A missing Spanish browser test or browser wrapper is shown as `SKIPPED` with the reason.

The current template stand-in execution test runs six everyday templates to verified `done`; the other ten have existing validation and provenance checks but no end-to-end stand-in runner. The table reports this coverage explicitly as a failure for the full 16-template exit requirement. This runner does not claim those ten templates completed.

## Checks included

- Every `docs/guide/*.md` page's local Markdown links and the screen's `settings/help` destinations.
- Template manifest hashes/reviewer fields, template contract/safety, and the existing six-template stand-in end-to-end test.
- English/Spanish dictionary key and placeholder parity using `glacier/web/scripts/check-i18n.mjs --fail`.
- `glacier/web/e2e/spanish.spec.mjs` through `bash ~/tools/e2e.sh` when both files exist.
- Existing backend checks for flow round trip, A2A, MCP memory stdio, ACP stand-ins, AG-UI events, and AGENTS.md.

The runner is intentionally glue around the existing checks; it does not implement alternative validators or test harnesses.
