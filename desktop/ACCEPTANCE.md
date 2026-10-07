# Desktop acceptance checks (written before implementation)

- `./check.sh` builds the Tauri debug app and verifies the resulting executable exists.
- Rust unit test `detects_installed_tools` confirms the tool scan returns every supported tool name and marks a fake executable as present.
- Low-resource mode is configured in `sidecar.json` and sets `GLACIER_LOCAL_MODEL=qwen3:0.6b` and `GLACIER_MAX_PARALLEL_RUNS=1` for the backend.
- The app starts the backend on loopback at an OS-assigned port, waits for `/api/node-types`, then opens the built Glacier screen with that port.
- First-run information is a bundled plain-language page; tool results are local and no setup-report endpoint is called.
