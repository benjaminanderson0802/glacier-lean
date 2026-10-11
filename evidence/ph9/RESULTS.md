# E-PH9 current verification — 2026-10-10

Source: `c17f52c0fbb4c9cc3bb49baaf7acec116d83c3e4`, branch `card/gf-E-PH9`.

This card adds verification evidence and claims only. Product code, flows, checks, acceptance files, dependencies/pins, and NORTHSTAR are unchanged. No feature worker or human approval was impersonated, no branch was merged, and nothing was pushed. No paid route was used.

## Existing checks completed

Commands use `/home/glacier/w/glacier-lean/.venv/bin/python` (`$PY` below).

| Command | Result | Evidence |
| --- | --- | --- |
| In `glacier/backend`: `$PY -m pytest -q tests/test_selfbuild_flows.py tests/test_selfbuild_install_commands.py tests/test_maintenance_flow.py tests/test_workspaces.py tests/test_merge_lock.py` | **34 passed**, 20.08s | [focused-tests.log](focused-tests.log) |
| At root: `$PY -m pytest -q glacier/importers templates bench tools/scan tools/catalog` | **3 failed, 76 passed**, 30.16s | [project-tests.log](project-tests.log) |
| In `glacier/web`: `npx tsc -b` | Exit 0 after private dependency provisioning | [tsc-isolated.log](tsc-isolated.log) |
| `node e2e/theme_lint.mjs` | Pass, 52 files | [theme-isolated.log](theme-isolated.log) |
| `node scripts/check-i18n.mjs --fail` | Pass, 2 dictionaries / 938 keys | [i18n-isolated.log](i18n-isolated.log) |
| `npm run build` | Pass | [web-build-isolated.log](web-build-isolated.log) |
| `node e2e/live_real_backend.spec.mjs` | Failed during real-backend startup; no browser assertions completed | [live-browser.log](live-browser.log) |
| `node e2e/core.spec.mjs` | Failed clicking New flow after the mock socket connected | [mock-core.log](mock-core.log) |

The original shared dependency directory lacked TypeScript. The committed package.json/package-lock.json were copied to a private temporary directory and `npm ci --no-audit --no-fund` installed 203 packages there; only this worktree's pre-existing untracked node_modules link was redirected. Shared dependencies and tracked lockfiles were not changed. Original failure logs are retained alongside the passing rerun logs.

## Live versus fixture evidence

- **Live public discovery:** `scan.discover_records()` fetched all five configured public sources without reported source failures. The existing license/activity/popularity filters produced zero eligible records and zero proposals. [Raw source/failure/proposal metadata](discovery-live.json), [proposal output](discovery-proposals.md). This demonstrates a real scan and safe non-adoption; it does not prove that a candidate was proposed or accepted.
- **Real backend in existing tests, fixture workers/data:** the focused suite starts isolated Uvicorn backends and exercises successful verified merges, rejection of protected-test deletion, failed-run non-merging, sequential merges, and fixed-gate installation. Those toy/fixture runs are not real Glacier feature shipments. Maintenance/package parser tests use stubbed command/network results.
- **Real screen attempt:** the existing live-browser spec launched the real backend, then timed out while DBOS/SQLite initialized. It did not reach its screen assertions. Host contention is a possible cause, not established.
- **Current live maintenance:** the capture driver waited for the shared suite lock without starting a backend or run. Once the required template gate was confirmed failing outside this card's scope, only this card's unstarted lock-wait process was stopped; [queue record](maintenance-queue.json). No running suite or other worker's process was stopped. The unused capture driver is retained for reproducibility, not as passing evidence.
- **Historical feature shipments:** the three practice run/merge records remain in `evidence/live/selfbuild_first_card.md`. Their merge objects are absent from this checkout ([object lookup](historical-objects.json)); no fresh real feature shipment is claimed.

## Remaining blockers and ownership

- [Project-board claim](../../vault/claims/2026-10-10-e-ph9-project-board.md): 20 templates versus the check's 16, a 300px position violating the 260-grid contract, and missing `tpl-email-inbox-note` preview. The saved feature flow must continue to reject this board. Template implementation/spec owners must resolve it independently.
- [Browser/environment claim](../../vault/claims/2026-10-10-e-ph9-live-browser-startup.md): real backend readiness timeout, mock click timeout, and pending current maintenance run.
- [Legacy-board claim](../../vault/claims/2026-10-10-e-ph9-legacy-test-board.md): `setup/run_core_tests.sh` deletes a fixed shared directory and mutates shared dependencies; `setup/live_codex_check.sh` uses an unauthenticated fixed-port API. Neither launcher was executed or edited. No real Codex worker smoke was claimed.
- [Dependency claim](../../vault/claims/2026-10-10-e-ph9-ui-dependencies.md): private lockfile installation resolved the missing-TypeScript blocker; browser failures remain separately open.

No full backend suite, full screen board, or new feature-flow verification was completed by this card. Existing PH9 checkpoint statuses are retained; the phase is not newly closed. PH5 is still in progress. The integrator must review dependencies and original shipment artifacts; a new feature needs all independent gates green plus actual owner sign-off before verified merge.

Anti-pattern review: this report separates fixture success, historical reports, and incomplete live runs to avoid status claims unsupported by current evidence. No replacement governance/runtime code or test weakening was introduced.
