# Desktop acceptance checks

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
