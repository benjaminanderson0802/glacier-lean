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

## PH4 exit: memory survives a full reinstall from git

The serial backend acceptance test `test_memory_survives_full_reinstall_from_git` in
`glacier/backend/tests/test_memory_reinstall_proof.py` runs
`bench/memory_reinstall/prove.py` against temporary `GLACIER_HOME` folders and a temporary local
bare Git remote. It saves Markdown with caller front matter and wiki links, files a claim through
the claims API, edits a note, and removes the original home. It clones the vault into a fresh home
and verifies the Memory API list, note bodies, resolved links and graph, the restored claim,
git-backed undo, and the Markdown compatibility checker.

Run the proof directly from the repository root:

```sh
PYTHON=/path/to/project/.venv/bin/python /path/to/project/.venv/bin/python bench/memory_reinstall/prove.py
```

The backend initializes the vault repository on startup but does not automatically rebuild the
disposable SQLite search/link index from an existing clone. The proof rebuilds only those derived
tables from restored Markdown before comparing Memory, without adding commits to the cloned vault.

Run its pytest wrapper from `glacier/backend`:

```sh
../../.venv/bin/python -m pytest -q tests/test_memory_reinstall_proof.py
```
