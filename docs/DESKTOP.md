# Glacier desktop app scaffold

This is a desktop scaffold until the existing screen adopts the desktop API-origin requirement below. Do not treat the desktop app as ready for users until that screen change is complete.

The desktop shell uses Tauri 2. The `desktop/src-tauri/` directory is the Tauri application. Its `frontendDist` points at `desktop/dist`. Tauri's `beforeBuildCommand` builds the existing screen from `glacier/web` and assembles it with the bundled first-run page; `desktop/dist/` is generated and ignored by git. The screen source is maintained separately and is not copied into or edited by the desktop project.

The shell reserves an available loopback port, starts the Python backend as a child process, waits for `GET /api/node-types`, and then opens the bundled screen. The backend does not serve the screen at `/`. The desktop shell injects `window.__GLACIER_API__` into bundled pages with the local backend URL (for example, `http://127.0.0.1:43127`); the screen must use this value for API requests and its events WebSocket. Tauri's content security policy allows that loopback port and the Tauri app origin. All API traffic stays on this computer.

## Screen requirements

The screen must prefix every API request and the events WebSocket URL with `window.__GLACIER_API__`, falling back to the current page's origin when that value is undefined. The desktop shell injects the local backend address into bundled pages. Until the screen implements and verifies this behavior, this remains a scaffold.

The backend will allow only `tauri://localhost`, `http://tauri.localhost`, and `https://tauri.localhost` as cross-origin callers; the integrator will add this backend policy. Do not edit the screen or backend as part of this desktop card.

The first window shows the bundled first-run page while the backend starts. It checks for Codex, Ollama, OpenCode, Gemini, and Git through a Tauri command. Missing tools do not prevent continuing, and the list is never sent to the backend or elsewhere. The page explains the check in plain language. If the engine cannot start or does not become ready within 45 seconds, the page explains that in plain language and points to `backend.log` in the app's local data folder. Backend output is written to that log. Closing the desktop app stops the sidecar.

## Low-resource mode

`desktop/sidecar.json` enables low-resource mode. The sidecar sets `GLACIER_LOCAL_MODEL=qwen3:0.6b` and `GLACIER_MAX_PARALLEL_RUNS=1` for the backend. The data location is user-local application data. The backend binds only to `127.0.0.1`.

## Linux packages

Linux release packages contain the Glacier backend Python source, its requirements file, and the node type catalog. They do not contain Python or a private Python environment. Install Python 3.12 on the machine before running Glacier; the first-run page explains this requirement if the `python3.12` command is missing. Backend Python dependencies must also be installed for the selected Python runtime as listed in the bundled `backend/requirements.txt`.

On Debian 12/Ubuntu 24.04 or a compatible distribution, install the Tauri Linux build prerequisites and build both packages from the repository checkout:

```sh
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev librsvg2-dev patchelf
cd desktop
npm ci
./package_linux.sh
```

The script checks the system packages, builds the screen, and runs `npx tauri build --bundles deb,appimage`. The `.deb` and `.AppImage` files are written under `src-tauri/target/release/bundle/`. `file` is needed to build the AppImage. FUSE is not required to inspect or extract an AppImage, though starting it for the packaging check uses `xvfb-run` when available.

Check the package contents and headless AppImage launch with:

```sh
cd desktop
./test_packaging.sh
```

The `.deb` check confirms the backend source, requirements and contract catalog are present. The AppImage check runs `--help` under `xvfb-run`; if that tool is missing, it prints a skip message.

## macOS (needs a Mac to build and sign)

Build macOS packages on a Mac with current Xcode command line tools, Rust 1.92, and Node.js/npm installed. The package includes backend source only, so install Python 3.12 and the packages listed in `backend/requirements.txt` on the target Mac.

```sh
xcode-select --install
cd desktop
npm ci
npx tauri build --bundles app,dmg
```

The `.app` and `.dmg` are written under `src-tauri/target/release/bundle/`. Signing and notarization require Apple developer credentials and are not performed by these commands.

## Linux sandbox build

The sandbox acceptance script builds the screen and Tauri application, then checks the executable:

```sh
cd desktop
./check.sh
```

The executable is `desktop/src-tauri/target/debug/glacier-desktop`. The script also checks that `desktop/dist/first-run/index.html` exists after assembling the front end. The bundle uses explicit Python source globs for backend root modules, `nodes/`, `routes/`, and requirements files; it excludes backend data, virtual environments, caches, and tests.

## Python packaging follow-up

`backend/.venv/bin/python` in `sidecar.json` is a development placeholder. Python itself is not included in this scaffold, so a distributable app needs that runtime assembled before launch. Assemble a platform-specific runtime with **python-build-standalone** and resolve/install pinned backend dependencies with **uv** into the app's private backend environment. Do not use PyInstaller. Bundle only dependencies whose licenses allow redistribution; keep backend data and runtime configuration under user-controlled local application data. The backend's node type catalog is bundled as `contract/node_types.json`; with the backend working directory set to `backend/`, `app.py` resolves its `../contract/node_types.json` path to that bundled file.

## Windows build on the owner's PC

1. Install Rust 1.92, Node.js/npm, and the Tauri 2 Windows prerequisites (Microsoft C++ Build Tools and WebView2 runtime).
2. Build the screen from the repository root with `cd glacier/web && npm ci && npm run build`.
3. Prepare the private Python runtime and backend environment as described above, placing the runtime's `python.exe` directly at the configured `venv_python` path and the backend package at `desktop/backend/`. Point `sidecar.json` directly to that runtime `python.exe`; do not launch through a `.venv` activation/launcher script. The Tauri app kills and waits for its direct backend child when the window closes.
4. From `desktop/`, run `npm ci` and `npx tauri build --debug` to check the Windows app. The configured `beforeBuildCommand` builds the screen and assembles `desktop/dist` automatically. For a release installer, run `npx tauri build`; the configured NSIS target produces an installer under `src-tauri/target/release/bundle/nsis/`.
5. Verify first run on a clean Windows account, including the tool list, local data location, and backend readiness before handing the app to users.
