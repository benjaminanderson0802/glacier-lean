# Desktop updates

The Settings > About screen integration is left for the integrator. Tauri injects `window.glacierUpdater.check()` and `window.glacierUpdater.install(version)`. `check()` returns `null` or `{ version, notes }`; `install(version)` rechecks the version and installs it. The screen should show the version and notes and call `install(version)` only after the owner selects **Install update**. The app also checks at startup and emits `glacier-update-available` with the same version and notes. No backend HTTP endpoint is needed.

Updates are verified by Tauri's updater signature. The public key is in `desktop/src-tauri/tauri.conf.json`; the private key belongs only in GitHub Actions secrets. Never commit, paste into chat, or print the private key or password.

## One-time owner setup

Run these commands in PowerShell on the owner's computer from the repository root. Keep the terminal private. The private key is written to the owner's profile and is not printed. The public key is printed so it can be copied into `tauri.conf.json`.

```powershell
npm --prefix desktop ci --no-audit --no-fund
New-Item -ItemType Directory -Force "$HOME\.tauri" | Out-Null
desktop\node_modules\.bin\tauri.cmd signer generate --write-keys "$HOME\.tauri\glacier-updater.key"
```

Choose a strong password when prompted and save it in the owner's password manager. The command prints the public key. Replace `REPLACE_WITH_TAURI_UPDATER_PUBLIC_KEY` in `desktop/src-tauri/tauri.conf.json` with that full public key, then commit the public key change.

Add the private key as a GitHub Actions secret without displaying its contents in command output:

```powershell
Get-Content -Raw "$HOME\.tauri\glacier-updater.key" | gh secret set TAURI_SIGNING_PRIVATE_KEY
```

Add the password through GitHub's secret prompt (it is hidden while typing):

```powershell
gh secret set TAURI_SIGNING_PRIVATE_KEY_PASSWORD
```

The release job runs on a `v*` tag push or manual dispatch. For manual dispatch, provide a version tag such as `v0.1.1` for the release commit. With both secrets configured, CI uses `tauri.release.windows.conf.json` to create and sign the Windows updater artifact, then publishes the installer and `latest.json` to that GitHub Release. Regular desktop builds use platform configs with updater artifacts disabled. If either secret is missing, the signed updater release is skipped with a clear message; ordinary installer builds remain available.

## Screen integration

The screen integration is left to the integrator. Import no updater package in the web project; call `window.glacierUpdater.check()` when About opens, show `version` and `notes`, and call `window.glacierUpdater.install(version)` only from the owner's explicit install button. The startup event is named `glacier-update-available`. The helper is available only inside the installed desktop app.
