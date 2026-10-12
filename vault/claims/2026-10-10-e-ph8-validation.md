---
id: CLM-2026-10-10-E-PH8-VALIDATION
filed_by: E-PH8
run_id: null
node_id: null
checkpoint: PH8.1
kind: environment
summary: Current desktop package and browser proofs require missing build tools and tester-owned check maintenance.
evidence: evidence/PH8/2026-10-10/
attempts_made: 1
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

The current worker has no Cargo/Rust, desktop node_modules, TypeScript, or Playwright in its linked web node_modules. `cargo test --locked --lib` exits 127. TypeScript, translation parity, web build and updater browser checks fail before exercising the application. Theme lint passes. This repeats the known environment gaps in CLM-2026-10-08-W89-RUST-TOOLCHAIN and CLM-2026-10-08-W89-UI-DEPENDENCIES. Reuse their resolution: provision an isolated environment from the existing locks and run the unchanged checks; do not mutate the shared dependency symlink while parallel workers use it. Package builds and browser proof are parked for that environment.

Separately, `desktop/test_packaging.sh` fails its literal Rust argument check: it expects `-m uvicorn`, but the shell intentionally starts `-s -m uvicorn` to exclude user-site packages. The Windows/Unix smoke scripts also still use the old arguments. The independent tester must align those checks with the existing safety behavior. This builder did not remove isolation, edit a check, or declare the packaging suite green.

The legacy `setup/run_core_tests.sh` installs into shared dependencies, removes fixed `/tmp/e2edata`, and starts a backend on fixed port 8000; `setup/live_codex_check.sh` sends unauthenticated writes to that fixed port. Running either unchanged risks other workers' state and does not reproduce the current authenticated application. They were inspected, not executed. The integrator/test owner must provide an isolated, authenticated board before phase closure. No worker implementation changed on this card, so no live model call is needed for its scoped fix.

Owner PC proof remains separate: the existing 0.2.0 installation must offer a later owner-approved signed update and install it only on click. No signing keys, release tags, publication, or paid CI were requested or used by this card. Manual dispatch of the current desktop workflow is **not** a build-only action: it can run release-windows and publish when signing secrets exist.

A fallback screenshot attempt with the existing cached Chromium binary also timed out (40 seconds). A fresh profile with DISPLAY/WAYLAND_DISPLAY removed, following `~/tools/e2e.sh`, timed out again (45 seconds) without producing an image. No third retry was made; browser rendering remains unverified.
