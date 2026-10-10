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
