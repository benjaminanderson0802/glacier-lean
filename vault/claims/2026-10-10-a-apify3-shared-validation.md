---
id: CLM-2026-10-10-A-APIFY3-SHARED-VALIDATION
filed_by: A-APIFY3
run_id: null
node_id: null
checkpoint: PH12.10
kind: environment
summary: Shared frontend dependencies and one backend startup prevent a clean project board for the Apify portfolio card
evidence: ventures/apify-portfolio/evidence/typescript.txt; ventures/apify-portfolio/evidence/i18n.txt; ventures/apify-portfolio/evidence/backend-core.txt
attempts_made: 1
status: filed
assigned_to: integrator
resolution: null
resolution_evidence: null
---

The three new Actor mains succeed against real official sources, and portfolio plus existing venture tests pass 52/52. No backend or screen implementation was changed.

Required screen checks were run once: `npx tsc -b` cannot load the project TypeScript compiler, and `node scripts/check-i18n.mjs --fail` reports ERR_MODULE_NOT_FOUND for typescript. Theme lint passes. The worktree's node_modules is a pre-existing symlink into the shared checkout. This matches the earlier claim [CLM-2026-10-08-W89-UI-DEPENDENCIES](2026-10-08-w89-ui-dependencies.md); its documented solution is installing locked dependencies in an isolated frontend environment. No package installation or shared-directory changes were attempted by this Actor worker.

`cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_core.py` ran to completion: 31 passed, 1 setup error in 255.19 seconds. `test_websocket_receives_node_events` failed because its uvicorn subprocess did not start within the 60-second fixture deadline; its captured backend log was empty. Cause beyond startup failure is not established. The suite did start and exercise real backends for the passing cases. No test/timeout changes or unbounded retries attempted.

The legacy setup/run_core_tests.sh installs into the shared venv/node_modules and removes a fixed /tmp/e2edata directory. It was inspected, not run against other workers' shared resources. The scoped core suite and screen checks above provide available evidence without those mutations. No worker node changed, so live_codex_check.sh is not applicable. The integrator should complete the full board in its isolated/shared-test lane and diagnose the startup error before claiming phase-wide acceptance. This claim does not assert a defect in the Actor packages or close either verification gap.
