# Glacier desktop app

The desktop shell and screen integration are implemented. Current Linux verification and remaining installer/PC checks are recorded in [PH8 evidence](../evidence/PH8/2026-10-10/README.md); this is not a release-readiness claim.

The desktop shell uses Tauri 2. The `desktop/src-tauri/` directory is the Tauri application. Its `frontendDist` points at `desktop/dist`. Tauri's `beforeBuildCommand` builds the existing screen from `glacier/web` and assembles it with the bundled first-run page; `desktop/dist/` is generated and ignored by git. The screen source is maintained separately and is not copied into or edited by the desktop project.

The shell reserves an available loopback port, starts the Python backend as a child process, waits for `GET /api/health`, and then opens the bundled screen. The backend does not serve the screen at `/`. The desktop shell injects `window.__GLACIER_API__` into bundled pages with the local backend URL (for example, `http://127.0.0.1:43127`); the screen uses this value for API requests and its events WebSocket. Tauri's content security policy allows that loopback port and the Tauri app origin. All API traffic stays on this computer.

The Tauri shell uses the pinned `tauri-plugin-single-instance` plugin. Launching Glacier again restores, shows and focuses the existing main window; the second process exits without starting another backend. The live events WebSocket sends the install token as a `Sec-WebSocket-Protocol` value (`glacier-events`, followed by the token). Older installed screens may still use `?token=` during the desktop update transition; the backend scrubs that query before Uvicorn logs it, and its access-log filter redacts token values as a second safeguard.

## Screen requirements

The screen prefixes API requests and the events WebSocket URL with `window.__GLACIER_API__`, falling back to the current page's origin when that value is undefined. The desktop shell also injects `window.__GLACIER_TOKEN__` for authenticated requests. See `glacier/web/src/api.ts` for the shared API client.

The backend recognizes `tauri://localhost`, `http://tauri.localhost`, and `https://tauri.localhost` as desktop origins; development origins require explicit development mode. See [local security](LOCAL_SECURITY.md).

The first window shows the bundled first-run page while the backend starts. It checks for Codex, Ollama, OpenCode, Gemini, and Git through a Tauri command. The AI tools are optional, but the current backend requires Git for vault history. The installer does not bundle a Git executable; see [the clean-machine prerequisite claim](../vault/claims/2026-10-10-e-ph8-git-prerequisite.md). The tool list is never sent to the backend or elsewhere. The page explains the check in plain language. If the engine cannot start or does not become ready within 45 seconds, the page explains that in plain language and points to `backend.log` in the app's local data folder. Backend output is written to that log. Closing the window hides it in the tray so automations can continue. Choosing **Quit Glacier** stops the sidecar. Python starts with `-s` and `PYTHONNOUSERSITE=1` to exclude unrelated packages from the user profile.

## Low-resource mode

`desktop/sidecar.json` enables low-resource mode. The sidecar sets `GLACIER_LOCAL_MODEL=granite3.3:2b` and `GLACIER_MAX_PARALLEL_RUNS=1` for the backend. The data location is user-local application data. The backend binds only to `127.0.0.1`.

The loading page uses the same room artwork, Nunito font, and colour tokens as the main screen. `desktop/test_first_run_theme.sh` checks that the bundled tokens and fonts match.

## Linux packages

Linux release packages contain the Glacier backend, its requirements file, the node type catalog, and a private CPython 3.12 runtime with the pinned backend packages. Users do not need a separate Python installation. Startup currently also requires a system Git executable; a package smoke run on a developer machine does not prove a clean-machine install without Git.

On Debian 12/Ubuntu 24.04 or a compatible distribution, install the Tauri Linux build prerequisites and build both packages from the repository checkout:

```sh
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev librsvg2-dev patchelf
cd desktop
npm ci
./package_linux.sh
```

The script checks the system packages, downloads and verifies the pinned standalone runtime, installs the pinned requirements, builds the screen, and runs `npx tauri build --bundles deb,appimage`. The `.deb` and `.AppImage` files are written under `src-tauri/target/release/bundle/`; the script prints their byte and KiB sizes. `file` is needed to build the AppImage. FUSE is not required to inspect or extract an AppImage, though starting it for the packaging check uses `xvfb-run` when available.

Check the package contents and headless AppImage launch with:

```sh
cd desktop
./test_packaging.sh
```

The `.deb` check confirms the backend source, requirements, contract catalog, and Python runtime are present, extracts the package, and checks `import fastapi, dbos`. The AppImage check runs `--help` under `xvfb-run`; if that tool is missing, it prints a skip message.

## macOS (needs a Mac to build and sign)

Build macOS packages on an Apple Silicon Mac with current Xcode command line tools, Rust 1.92, and Node.js/npm installed. Build the bundled runtime first with `python3 ../setup/pybundle/build_runtime.py --platform aarch64-apple-darwin` from `desktop/`; the app then includes Python and backend dependencies.

```sh
xcode-select --install
cd desktop
npm ci
npx tauri build --config src-tauri/tauri.macos.conf.json --bundles app,dmg
```

The `.app` and `.dmg` are written under `src-tauri/target/release/bundle/`. Signing and notarization require Apple developer credentials and are not performed by these commands.

## Linux sandbox build

The sandbox acceptance script builds the screen and Tauri application, then checks the executable:

```sh
cd desktop
./check.sh
```

The executable is `desktop/src-tauri/target/debug/glacier-desktop`. The script also checks that `desktop/dist/first-run/index.html` exists after assembling the front end. The bundle uses explicit Python source globs for backend root modules, `nodes/`, `routes/`, and requirements files; it excludes backend data, virtual environments, caches, and tests.

## Bundled Python runtime

`setup/pybundle/build_runtime.py` downloads CPython 3.12.15 from python-build-standalone release `20261003`, checks a pinned SHA-256 for each supported target, safely extracts it, and installs `setup/requirements.txt`. It supports `x86_64-unknown-linux-gnu`, `aarch64-apple-darwin`, and `x86_64-pc-windows-msvc`. Runtime files are ignored by Git and included as Tauri resources when present. Backend data and runtime configuration remain under user-controlled local application data. The backend's node type catalog is bundled as `contract/node_types.json`; with the backend working directory set to `backend/`, `app.py` resolves its `../contract/node_types.json` path to that bundled file.

The standalone runtime includes `LICENSE.txt` under the PSF License. The builder preserves it in the bundle. Third-party backend packages retain their individual license files under their `*.dist-info` metadata folders in `site-packages`; review these before redistributing an installer. Pip is used only at build time, and its bundled license notices are retained with the runtime.

## Windows build on the owner's PC

1. Install Rust 1.92, Node.js/npm, and the Tauri 2 Windows prerequisites (Microsoft C++ Build Tools and WebView2 runtime).
2. Build the screen from the repository root with `cd glacier/web && npm ci && npm run build`.
3. Build the Windows runtime from the repository checkout. From the repository root run `python setup/pybundle/build_runtime.py --platform x86_64-pc-windows-msvc`, then build from `desktop/`. This cross-downloads the Windows interpreter and resolves binary wheels using `pip --platform win_amd64 --only-binary=:all:`; Windows itself is not needed for this preparation step.
4. From `desktop/`, run `npm ci` and `npx tauri build --config src-tauri/tauri.windows.conf.json --debug` to check the Windows app. The configured `beforeBuildCommand` builds the screen and assembles `desktop/dist` automatically. For a release installer, run `npx tauri build --config src-tauri/tauri.windows.conf.json`; the configured NSIS target produces an installer under `src-tauri/target/release/bundle/nsis/`.
5. Verify first run on a clean Windows account, including the tool list, local data location, and backend readiness before handing the app to users.

## Windows installer check in GitHub Actions

The `desktop` workflow runs on pull requests that change `desktop/`, `glacier/`, `setup/pybundle/`, or the workflow itself, and has a manual release dispatch. **Do not dispatch it merely to verify a build:** the same workflow can publish a signed Windows release when signing secrets are configured. Release dispatch and version tags remain owner steps. It builds the pinned Windows Python runtime, packages the NSIS installer, and smoke-tests installation, backend readiness, and the engine token on a temporary CI runner. The workflow is marked non-blocking while its first Windows runs are reviewed. It does not install anything on the owner's PC.

To download the installer, open the completed `desktop` workflow run on GitHub and download the `glacier-windows-installer` artifact from its Artifacts section. The artifact is retained for 7 days. The Windows runner smoke test does not replace the owner's later install and first-run check on his PC.

## Linux and macOS build artifacts in GitHub Actions

The same `desktop` workflow also builds Linux packages on `ubuntu-latest` and an Apple Silicon macOS app on `macos-latest`. Both jobs are non-blocking while their first runs are reviewed. Linux CI builds the bundled x86_64 Python runtime, `.deb`, and AppImage; it extracts each package and checks backend readiness and token protection without FUSE. macOS CI builds the bundled Apple Silicon runtime, `.app`, and `.dmg`, then checks backend readiness and token protection from inside the app bundle. Builds are unsigned for now. The smoke tests run only on temporary CI workers and install nothing on an owner machine.

To download a build, open the completed **desktop** workflow run on GitHub and choose its artifact:

- `glacier-linux-packages` contains the `.deb` and `.AppImage` files.
- `glacier-macos-dmg` contains the `.dmg` disk image.

These artifacts are kept for 7 days. Download them from the Actions run's **Artifacts** section before they expire.

## Remaining owner PC checks

- After the Git prerequisite claim is resolved, on a clean Windows account, double-click the installer and launch Glacier without developer Python/Node/Rust/Git. Confirm the loading page, tool detection, and main screen; run an offline starter to a saved, verified result. Preserve installer version, run id and output as evidence.
- Confirm a second launch focuses the existing window, closing keeps scheduled work running, and **Quit Glacier** stops its backend. Check logon startup separately.
- After the owner approves a later signed release, use the installed 0.2.0 app's Settings > About to check, review the version/notes, and click **Install update**. Restart and confirm the new version plus preserved vault/settings. Linux fixture tests do not prove this upgrade.
- Windows trust prompts and signing/distribution remain owner concerns; this card does not change machine security settings, generate signing keys, or publish a release.

PH8.1 remains in progress until the actual Windows update proof exists. The phase exit additionally requires the clean-machine installer-to-first-automation proof. Current macOS packaging must be verified on macOS; historical CI evidence is not a fresh run.
