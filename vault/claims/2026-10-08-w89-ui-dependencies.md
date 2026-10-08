---
id: CLM-2026-10-08-W89-UI-DEPENDENCIES
filed_by: W89-declutter-shell
run_id: null
node_id: null
checkpoint: PH10.3
kind: environment
summary: UI checks cannot load pinned TypeScript because the shared node_modules target is empty
evidence: "bash ~/tools/e2e.sh acquired the lock and passed theme lint, then failed at node scripts/check-i18n.mjs --fail with ERR_MODULE_NOT_FOUND for typescript; glacier/web/node_modules links to /home/glacier/w/glacier-lean/glacier/web/node_modules, which contains no packages"
attempts_made: 2
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The repository's web dependencies are pinned in `glacier/web/package-lock.json`, but this worktree's `node_modules` link points to an empty shared directory. The full UI check passed theme lint and stopped before translation parity, type-check, build, and e2e because the checker could not import `typescript`. I did not install or replace packages in the shared directory while other workers were using the screen-test lock. The dedicated window-controls e2e and after screenshot could not run. Install the lockfile dependencies in an isolated web `node_modules` directory, then run `bash ~/tools/e2e.sh` and capture the after screenshot before closing this claim.
