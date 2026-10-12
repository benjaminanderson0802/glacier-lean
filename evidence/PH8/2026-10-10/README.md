# PH8 Linux verification — E-PH8, 2026-10-10

PH8.1 remains **in progress**. This card does not release, publish, sign, or advertise Glacier. No acceptance check or ACCEPTANCE.md was edited.

## Drift check, recorded before implementation

1. Checkpoints: PH8.1 desktop packaging/update proof, PH8.3 first-run setup, and PH8.4 Linux resources. Owner Benjamin assigned this card on 2026-10-10 to maximize progress.
2. Dependencies: PH7 has an owner-approved exit. All PH1 checkpoints have linked done evidence, but its phase status remains in progress; this card does not establish its phase-wide audit exit. The assigned card authorizes parallel work, not automatic phase closure.
3. Properties/metrics: P-USABLE and M-TTFA (installation and readable first-run UI); P-CONTROL/P-SECURE and M-SECURITY (explicit update installation, signatures, authenticated local backend). No first-user timing was measured.
4. Existing tools: retain Tauri, python-build-standalone, the existing room assets, and current packaging scripts. Only desktop presentation glue and documentation changed; no new dependency or paid tool was adopted.
5. Acceptance specified first: unchanged `desktop/ACCEPTANCE.md`, `desktop/test_first_run_theme.sh`, `desktop/test_packaging.sh`, `desktop/test_updater_config.py`, `setup/pybundle/test_build_runtime.py`, and backend install-layout/starter/system checks. The theme check failed before the fix and passed afterward. `docs/ACCEPTANCE.md` reserves the Windows clean-install/first-automation proof for the existing installer smoke.

## What changed

Commit `91731ea` brings the desktop loading page into the current painted room: exact shared colour tokens, bundled Nunito plus its OFL notice, existing room artwork, frosted panel and pill button styling, lowercase chrome, smooth/reduced-motion loading indicator. Existing element ids and tool/error behavior are preserved. A subsequent copy correction identifies Git as required for note history, after the no-Git startup dependency was reproduced. An explicit hidden rule prevents the flex loading row overriding its hidden state after a startup error.

`docs/DESKTOP.md` and `docs/UPDATES.md` now describe the implemented API/updater integration, health probe, user-site isolation, granite default, tray close/quit distinction, release-dispatch behavior and outstanding PC proof. No source or mock backend behavior changed.

## Checks and limits

Commands run from the repository root unless a directory is shown. Project interpreter: `~/w/glacier-lean/.venv/bin/python`.

Continuation rerun after the interrupted worker: `bash desktop/test_first_run_theme.sh` passed; `node --check desktop/first-run/app.js` passed; `~/w/glacier-lean/.venv/bin/python -m pytest -q setup/pybundle/test_build_runtime.py desktop/test_updater_config.py` passed (10); and from `glacier/backend`, `~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_install_layout.py tests/test_starter.py tests/test_system_check.py` passed (30). `node scripts/check-i18n.mjs --fail`, `npx --no-install tsc -b`, and `node e2e/updates.spec.mjs` were retried and remain blocked because the shared linked `glacier/web/node_modules` lacks TypeScript and Playwright. See [continuation-checks.log](continuation-checks.log); no dependency symlink or acceptance check was changed.

| Command | Result and evidence | Proof scope |
| --- | --- | --- |
| `bash desktop/test_first_run_theme.sh` | Fails before, passes after: [before](first-run-theme-before.log), [after](first-run-theme-after.log) | Exact theme/font parity and token-only loading-page styles |
| `node --check desktop/first-run/app.js` | Exit 0 | JavaScript syntax only |
| Project Python `-m pytest -q setup/pybundle/test_build_runtime.py desktop/test_updater_config.py` | **10 passed**: [log](runtime-updater.log) | Fixture archives/wheel commands and static updater config; no downloaded-update signature/install proof |
| From `glacier/backend`: project Python `-m pytest -q tests/test_install_layout.py tests/test_starter.py tests/test_system_check.py` | **30 passed**: [log](backend-desktop.log) | Resource-layout import probe, real isolated HTTP backends for apply/settings, and simulated hardware/model detection |
| From `glacier/web`: `node e2e/theme_lint.mjs` | **Passed, 52 files**: [log](theme-lint.log) | Main-screen source lint |
| From `glacier/web`: `npx --no-install tsc -b`; `node scripts/check-i18n.mjs --fail`; `npm run build`; `node e2e/updates.spec.mjs` | **Blocked**: [TypeScript](typescript.log), [i18n](i18n.log), [build](web-build.log), [updater UI](updates-ui.log) | Linked shared dependencies lack TypeScript and Playwright; updater bridge spec did not execute |
| `bash desktop/check.sh`; from `desktop/src-tauri`: `cargo test --locked --lib` | **Blocked**: [desktop](desktop-check.log), [Rust](rust-tests.log) | Frontend dependency and Cargo absence; no Tauri binary built |
| `bash desktop/test_packaging.sh` | **Failed**: [log](packaging.log) | Tester-owned literal command check expects the old launch arguments; did not remove `-s` isolation to satisfy it |

The interrupted worker also started the full backend suite; [backend-full.log](backend-full.log) ends at 17% with no pytest summary or exit status, so it is incomplete and is not counted as a pass or a failure result.

The live first-run render and desktop Rust suite remain unverified. Cargo is not installed, browser launch previously timed out, and the remaining browser checks cannot load Playwright from the current shared dependency link. The continuation reran the passing theme, runtime/updater fixture, and backend resource/starter checks above; it did not attempt to repair the shared toolchain.

The cached Chromium fallback did not produce a screenshot: initial 40-second attempt timed out; a fresh profile with DISPLAY/WAYLAND_DISPLAY removed also timed out after 45 seconds. No third attempt. Rendering and native Tauri tool detection remain unverified in this worker.

## Clean-machine prerequisite gap

With PATH empty, importing the installed GitPython dependency fails before vault initialization: [no-git.log](no-git.log). The resource manifest does not bundle Git. [CLM-2026-10-10-E-PH8-GIT-PREREQUISITE](../../../vault/claims/2026-10-10-e-ph8-git-prerequisite.md) records this unresolved installer prerequisite. The loading page now identifies Git as required rather than promising every tool is optional.

## Remaining proofs

See [remaining owner PC checks](../../../docs/DESKTOP.md#remaining-owner-pc-checks). A real NSIS double-click install and a version-to-version signed update from installed 0.2.0 remain PC checks. The owner decides when any later release exists. macOS build/startup needs macOS. Linux package/shell checks need the build environment restored. Historical PR evidence in NORTHSTAR is not a fresh build of this branch.

[CLM-2026-10-10-E-PH8-VALIDATION](../../../vault/claims/2026-10-10-e-ph8-validation.md) records missing tooling, stale independent packaging checks and the unsafe shared-state assumptions in the legacy core-board scripts. `setup/run_core_tests.sh` was inspected rather than allowed to reinstall shared dependencies and remove another worker's fixed data directory. No worker code changed; the unauthenticated fixed-port live Codex script was not invoked.

Anti-pattern review: fixed obsolete presentation and stale implementation claims; retained passing evidence separately from unverified desktop/platform claims. Recorded the finding in `docs/AMENDMENTS.md`; no mission, invariant or exit criterion changed.
