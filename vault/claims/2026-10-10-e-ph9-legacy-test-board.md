---
id: CLM-2026-10-10-E-PH9-LEGACY-TEST-BOARD
filed_by: E-PH9
run_id: null
node_id: null
checkpoint: PH9.1
kind: environment
summary: Legacy board scripts use a shared destructive path and unauthenticated fixed-port API
evidence: setup/run_core_tests.sh; setup/live_codex_check.sh
attempts_made: 0
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

`setup/run_core_tests.sh` unconditionally removes `/tmp/e2edata`, uses shared port 8000, and reinstalls into the shared dependency directory. `setup/live_codex_check.sh` addresses that fixed port without the required engine token. The scripts were inspected but not executed, because this card may not delete another worker's data or mutate their dependency installation. No process belonging to another worker was stopped.

Existing safer components are available: the backend pytest server fixture allocates isolated homes/free ports, and `glacier/web/e2e/live_real_backend.spec.mjs` uses an isolated authenticated real backend. This card runs those existing components and a fresh-home maintenance Environment instead. The integrator/test owner should update the legacy launchers independently; E-PH9 must not edit checks that judge itself.
