# PH12.22 final integration audit

Auditor: I3 integrator. This records integration evidence and release gaps; integration is not a launch claim.

## Drift check

- Checkpoint: PH12.22, integration and independent audit.
- Dependencies: PH12 depends on PH5 and PH9. PH5 remains in progress, so PH12.22 stays in progress even though this card was authorized to start.
- Defining properties and metrics: P-VERIFY, P-LOOPS, P-CONTROL, P-USABLE; M-AUDIT, M-INTERVENE, and M-RECOVER.
- I-01: reuse Glacier's installed runtime, DBOS schedules, and the shared venture blocks. Installer code is glue for this repository's manifests; no paid or closed service was added.
- Acceptance: run every block `CHECK.md`, all venture tests, the full backend pytest suite, and `npm run check:ui`; install into a disposable real Glacier home; repeat installation without changing the 31 flow IDs; inspect every venture's steps, dry-run flow, and history in Glacier; commit test logs and screenshots.

## Integration fixes

- CPSC source IDs and input fields now match the merged ruleset.
- Co-op intake now uses the shared reader, rules checker, and deadline tracker. USPS EDDM output validates flat dimensions and weight. The co-op test assertion was updated because it described the pre-merge state where the shared rules block was absent; the merged block now accepts the complete valid fixture. No other test was changed to hide a failure.
- Grouped secret steps are presented once in the Your Steps inbox and saved to Glacier's local secret store. Venture setup and approval steps also appear in Home's needs-you queue. Home shows one daily venture digest across installed ventures.
- Repeated installation skips unchanged flows. Two repeat installs kept all 31 flow IDs unchanged; all 12 installed schedules declare missed-run `run_once` and overlap `skip`.
- Owner run summaries show plain text instead of raw output JSON. The Apify deployment step now uses plain instructions and a guide link instead of a shell command.
- The UI board exposed a short flow canvas at 1024x700 and a Home starter panel whose automation list overflowed into Needs You. The build panel now grows in short, narrow windows, and the starter list scrolls inside its own panel so both sets of controls remain reachable.

## Verification

- Block checks: 49 passed across connectors (11), customer (10), deadlines (6), feeds (9), filer (3), mail (4), reader (3), and rules (3). Reader benchmark: 100% agreement and 100% labeled-value accuracy on 7 fields.
- Venture tests: 163 passed, 3 subtests passed, 2 failed. Failure names and causes are below.
- Full backend: 828 passed, 1 skipped, 3 failed, 5 warnings. The full-suite run used `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests` from `glacier/backend`.
- Full UI board: `GLACIER_PYTHON=/home/glacier/w/glacier-lean/.venv/bin/python npm run check:ui` from `glacier/web`; final run passed all 30/30 board steps. The first full run had a transient Messenger live-event assertion failure; the fresh full run passed without changing the check. See `evidence/ventures/I3-ui-check-ui.log`.
- Final Home queue integration check: `node e2e/ventures.spec.mjs` passed all 15 assertions; `tests/test_ventures.py` passed all 7 tests after setup and approval items were added to Home's needs-you list.
- Real Glacier: installed 31 flows and 12 schedules in a disposable home; all 11 primary venture dry-runs reached a final status (2 done, 9 waiting at owner approvals). Captured home, needs-you, Your Steps inbox, 11 venture cards, 11 run views, and 11 history views in `evidence/ventures/final-*.png`.
- Live real-backend UI check: passed after selecting the project venv; real backend events, flow run output, Ask fake-engine reply, and messenger live reply all appeared. See `evidence/ventures/I3-live-ui-targeted.log`.
- Live Codex setup check: the real Codex node created `hello.txt`, but the setup script's following `cat` node failed because its literal `${GLACIER_HOME:-...}` path was nested under the Codex workspace. The check script was not changed. See `evidence/ventures/I3-live-codex-check.log`.

## Remaining issues

- `ventures/recall-checker/tests/test_recall_checker.py::RecallMatcherAcceptanceTests::test_clean_item_uses_required_source_and_date_vocabulary` expects `no match in ...`, while the venture spec requires `no match found in ...`. The implementation follows the spec; the open vocabulary claim remains unresolved.
- `ventures/tests/test_install_all.py::InstallAllTests::test_discovery_is_data_driven_and_only_filters_by_slug` assumes the repository contains only Apify flows; integration now discovers 31 venture flows. This stale acceptance test remains unchanged.
- Backend failures: the email-trigger template cannot be manually run (`This step starts when a new email arrives`); the email-search template has no `EMAIL_APP_PASSWORD`; the local-data-pipeline structured-AI node returned text that did not parse as JSON. These require separate template/runtime disposition and are not venture integration failures.
- The live Codex setup script has the workspace-path issue above. The `setup/run_core_tests.sh` embedded browser check uses an unauthenticated backend and failed its authenticated WebSocket/API calls; see `evidence/ventures/I3-core-board-prior.log`. The project-venv full pytest and authenticated UI board are run separately here.
- Government-feed live rechecks after the parser fixes were not completed. Existing feed evidence records source-format, 403, consent-shell, and timeout alerts; do not treat those sources as release-verified. Owner API accounts/keys were not available for Jobber, Shopify, ShipStation, or Stripe live reads.
- Venture cards expose daily run counts and statuses, with a combined daily digest on Home. A generated narrative daily report file for every venture was not verified.
- PH12.22 remains `in_progress`; PH5 has not reached its exit, and PH12 has unresolved release evidence and owner setup steps. No PH12 checkpoint was marked done.

## Evidence files

- `evidence/ventures/I3-final-checks.md` — exact board commands and counts.
- `evidence/ventures/I3-live-walkthrough.json` — live run IDs and statuses.
- `evidence/ventures/installer-idempotence.json` — stable IDs and schedule policy checks.
- `evidence/ventures/final-*.png` — owner-facing screens.
- `evidence/ventures/*-tests.log` — captured command output.

## I4 final2 verification (2026-10-10)

### Integration changes

- Merged `card/gf-X1`, `card/gf-X2`, and `card/gf-X3` into I4 with three merge commits: `0bfd1db`, `49ae4ca`, `081675b`.
- Kept I3 shared-file integrations and each fixer’s venture changes. In the CPSC merge, removed old shadowed block aliases so `cpsc_prep.py` imports the shared reader, rules, and feeds functions correctly.
- Set OSHA's installed and manifest schedules to `missed_run: run_once`, `overlap: skip`; made the warranty Jobber setup step name all four required secret fields.
- Reworked `OWNER-START-HERE.md` into the same 12-venture order, step titles, and link order shown in Glacier. Programmatic comparison of each step and link array against the manifests passed. Added unresolved independent-review items under `known limits`.
- Did not edit tests.

### Final board results

- **Venture tests:** 189 passed and 3 subtests passed; 2 failed across 21 test directories. `ventures/recall-checker/tests/test_recall_checker.py::RecallMatcherAcceptanceTests::test_clean_item_uses_required_source_and_date_vocabulary` expects `no match in ...`, while the shared output rule requires `no match found in ...`. `ventures/tests/test_install_all.py::InstallAllTests::test_discovery_is_data_driven_and_only_filters_by_slug` still expects all discovered flows to belong to Apify (2), although discovery correctly finds 34 flows across ventures. Both assertions are unchanged.
- **Local block checks:** 51 passed across connectors (11), customer (10), deadlines (6), feeds (11), filer (3), mail (4), reader (3), and rules (3). Reader benchmark: 100% agreement and 100% labeled-value accuracy across 7 fields.
- **Live feed CHECK:** both `sync-all` passes exited 1 because source alerts remain. First pass: CPSC flagged codes, rule codes, and registry template each returned HTTP 403; CPSC recalls returned 10,047 rows but timed out; NHTSA returned 245,855; FDA enforcement 87,586; FSIS HTTP 403; OSHA ITA 400,288; DIBBS 0 rows with the DoD warning/consent redirect; Cook County staged 50,000 of 1,864,270 2026 rows. On repeat, unchanged sources reported `changed: false`; CPSC recalls returned 10,047 without an alert; Cook County advanced staging to 100,000 of 1,864,270. The previous complete Cook County snapshot remains active.
- **Full backend:** 820 passed, 1 skipped, 11 failed, 5 warnings in 24m 29s. Three assistant-chat tests and one verification test timed out waiting on API responses. Three template tests failed because the email-arrival trigger cannot be manually started, `EMAIL_APP_PASSWORD` is not configured, and the local structured-AI output was invalid JSON. Three Home tests found 36 baseline venture needs-you entries where the old empty state expected zero, 39 rather than 3 after adding three runs, and a venture item without the `ref.run_id` field expected at the head of the queue. The paused-schedule test saw no resumed runs within 25 seconds. Full trace and names are in `evidence/ventures/final2-backend-tests.log`.
- **UI board:** `npm run check:ui` passed all 30/30 steps on the clean rerun, including `every_control.spec.mjs` and the real-backend venture screen checks. See `evidence/ventures/final2-ui-check-ui.log`.
- **Required shared core wrapper:** TypeScript and Vite build passed. The wrapper's backend rerun reported 825 passed, 1 skipped, 6 failed, and 5 warnings in 12m 51s; its script only retained the last three pytest lines, so the complete failure list is unavailable. The core browser check failed a 10-second selector wait. Its backend log shows unauthenticated API requests returning 401 and the events WebSocket returning 403. The wrapper's `uv` bootstrap also failed because `uv` is absent and system Python rejects user installs under PEP 668; it continued with existing dependencies. See `evidence/ventures/final2-core-board.log` and `/tmp/backend.log`.
- **Live Codex setup check:** did not create a run; its unauthenticated API calls returned 401 (`This request isn't from your Glacier app.`), followed by missing `run_id`/`status` parse errors. See `evidence/ventures/final2-live-codex-check.log`.

### Real Glacier integration

- `ventures/install_all.py --dry-run` validated 34 flows across 12 ventures. Two real installs into a disposable `GLACIER_HOME` preserved the same 34 IDs; the second install reported 34 unchanged and 0 saved. See the three install JSON evidence files.
- All 12 ventures appeared in the Glacier ventures view. The captured exact step order and link arrays match the manifests. There are 26 screenshots named `evidence/ventures/final2-*.png`, including the venture list, Your Steps, every card, and every run view.
- A dry-run of each venture's main flow was started. Results: Apify and Recall completed; Co-op, Utility Audits, and Warranty waited at `mail_approval`, `confirm_state`, and `review_draft`; Carpenter's Goods, CPSC, DIBBS, FDA, Freight, OSHA, and Property Tax failed because their disposable home had no required incoming product, batch, solicitation, brand-details, claim-intake, OSHA intake, or property case file. Recall completed with `check_done=no` because its inventory CSV was absent. No account credentials or customer records were supplied. The per-run output is in `evidence/ventures/final2-live-walkthrough.json`.
- `npm run live` started the real backend/UI for the walkthrough. Glacier displayed the venture cards and Your Steps in manifest order; screenshots and run histories are the `final2` artifacts above.

### Remaining release issues

- The two venture assertions, 11 full-backend failures, block-feed alerts, and core/live-Codex auth failures above remain unresolved; no judging test was changed. The wrapper's second backend result is the separately captured 6-failure run.
- Seven main flows need realistic owner-provided intake files before they can produce their draft outputs. Recall needs an inventory CSV; its completed dry-run only reported no match because none was present.
- The remaining independent review items and launch holds are listed in `OWNER-START-HERE.md` under **known limits**. No external submission, purchase, publication, or email send was performed.
- PH12.22 remains `in_progress`; this checkpoint's PH12.22 evidence field was updated with the verified `final2` logs, JSON, and screenshot paths. No checkpoint was marked done.

### I4 evidence

- `evidence/ventures/final2-venture-tests.log`, `final2-block-checks.log`, `final2-backend-tests.log`, `final2-ui-check-ui.log`, `final2-core-board.log`, and `final2-live-codex-check.log` — board outputs.
- `evidence/ventures/final2-install-dry-run.json`, `final2-install-first.json`, `final2-install-second.json`, and `final2-installer-idempotence.json` — dry-run and idempotence evidence.
- `evidence/ventures/final2-live-walkthrough.json` and `final2-*.png` — 12 ventures, dry-run outcomes, visible owner steps, cards, and run views.
