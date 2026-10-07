# Glacier desktop app

The desktop shell uses Tauri 2. The `desktop/src-tauri/` directory is the Tauri application. Its `frontendDist` points at `desktop/dist`, which `check.sh` assembles from the already built screen in `glacier/web/dist` plus the first-run page. The shell reserves an available loopback port, starts the Python backend as a child process, waits for `GET /api/node-types`, and then opens the screen from that local backend address. Navigation is restricted to Tauri's app pages and that backend port. API requests and the events WebSocket therefore stay on the same computer. No remote service is used by the desktop shell.

The first window shows the bundled first-run page while the backend starts. It checks for Codex, Ollama, OpenCode, Gemini, and Git through a Tauri command. Missing tools do not prevent continuing, and the list is never sent to the backend or elsewhere. The page explains the check in plain language. If the engine cannot start or does not become ready within 45 seconds, the page explains that in plain language and points to `backend.log` in the app's local data folder. Backend output is written to that log. Closing the desktop app stops the sidecar.

## Low-resource mode

`desktop/sidecar.json` enables low-resource mode. The sidecar sets `GLACIER_LOCAL_MODEL=qwen3:0.6b` and `GLACIER_MAX_PARALLEL_RUNS=1` for the backend. The data location is user-local application data. The backend binds only to `127.0.0.1`.

## Linux sandbox build

The sandbox acceptance script builds the screen and Tauri application, then checks the executable:

```sh
cd desktop
./check.sh
```

The executable is `desktop/src-tauri/target/debug/glacier-desktop`. The script also checks that `desktop/dist/first-run/index.html` exists after assembling the front end. The bundle uses explicit Python source globs for backend root modules, `nodes/`, `routes/`, and requirements files; it excludes backend data, virtual environments, caches, and tests.

## Python packaging follow-up

`backend/.venv/bin/python` in `sidecar.json` is a development placeholder. Python itself is not included in this scaffold, so a distributable app needs that runtime assembled before launch. For a redistributable Windows package, assemble a platform-specific runtime with **python-build-standalone** and resolve/install pinned backend dependencies with **uv** into the app's private backend environment. On Windows, the configured executable path will be `backend/.venv/Scripts/python.exe`. Do not use PyInstaller. Bundle only dependencies whose licenses allow redistribution; keep backend data and runtime configuration under user-controlled local application data.

## Windows build on the owner's PC

1. Install Rust 1.92, Node.js/npm, and the Tauri 2 Windows prerequisites (Microsoft C++ Build Tools and WebView2 runtime).
2. Build the screen from the repository root with `cd glacier/web && npm ci && npm run build`.
3. Prepare the private Python runtime and backend environment as described above, placing it at `desktop/backend/.venv/Scripts/python.exe` and the backend package at `desktop/backend/`.
4. From `desktop/`, run `npm ci` and `npx tauri build --debug` to check the Windows app. For a release installer, run `npx tauri build`; the configured NSIS target produces an installer under `src-tauri/target/release/bundle/nsis/`.
5. Verify first run on a clean Windows account, including the tool list, local data location, and backend readiness before handing the app to users.
