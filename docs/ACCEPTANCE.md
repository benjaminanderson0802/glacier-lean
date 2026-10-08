# Acceptance checks

## PH0 exit: core tools and legacy cleanup

Run `.venv/bin/python bench/ph0/run_ph0.py` from the repository root. It checks the pinned
Python and JavaScript core tools, their installed import/version/licence metadata, the repository
setup markers, every explicit legacy module row, and whether current evidence exists for disabled
prior systems. Tool metadata is read from the active Python environment and `glacier/web/node_modules`;
the PH0.4 check stays FAIL until current, inspectable evidence replaces its historical session log.
It does not change dependencies or run the full health board. `setup/health_check.py` remains the
integration health runner; run it separately when a full sandbox health check is needed.

Result on 2026-10-08 in this worktree: **FAIL**. DBOS, GitPython, repository setup and 51 legacy
entries passed. MAF and ACP had no recorded licence metadata; Bifrost had no pinned/importable Python
package; the four JavaScript packages were absent from `node_modules`; and current disabled-state
evidence for Forge tasks/containers was unavailable. The runner reports each item with its evidence.

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
