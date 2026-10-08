---
id: CLM-2026-10-08-W68-CHECK-UI
filed_by: W68-spanish-check
run_id: null
node_id: null
checkpoint: PH10.3
kind: environment
summary: check:ui is blocked by repeated Chromium core screen timeout before Spanish and updates specs run
evidence: "bash ~/tools/e2e.sh npm run -s check:ui; three runs failed at e2e/core.spec.mjs:85 while clicking data-testid=new-env, with Playwright saying the button never became stable (30 s timeout). bash ~/tools/e2e.sh node e2e/spanish.spec.mjs passes after the Spanish layout fixes. bash ~/tools/e2e.sh node e2e/updates.spec.mjs has also intermittently timed out taking its About full-page screenshot after fonts loaded."
attempts_made: 3
status: filed
assigned_to: null
resolution: null
resolution_evidence: null
---

The requested Spanish fixes and screenshots are ready, but the `check:ui` acceptance command cannot reach the Spanish spec because the existing core spec repeatedly times out on the `new-env` button. The same failure occurred on three fresh wrapped runs; the button is found, but Playwright never considers it stable. No core test or check was changed.

The newly included updates spec also has unstable browser results: an initial duplicate About test ID was fixed by giving the screen panel a distinct ID and keeping the update check available after install, but a later clean run timed out during the full-page About screenshot after fonts loaded. A separate run passed through the update/install checks and then timed out locating the recheck control while the screen was in its restart state; the screen now keeps the control available in that state. Further investigation is needed in the Chromium screen-test environment or the existing test flow.
