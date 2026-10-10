# PH12.22 final verification record

## Drift check and acceptance

- Checkpoint: PH12.22, final integration and independent coherence audit.
- Dependencies: PH5 is still in progress, so PH12.22 stays `in_progress`; the assigned card was authorized to start independently.
- Defining properties: P-VERIFY, P-LOOPS, P-CONTROL, P-USABLE. Metrics: M-AUDIT, M-INTERVENE, M-RECOVER.
- I-01: the runtime, DBOS schedules, and shared venture blocks already provide execution; this work integrates existing manifests and owner controls rather than adding another scheduler or paid service.
- Acceptance written first: run all block checks, all venture tests, full backend pytest, and the full UI board; install into a disposable live Glacier, prove repeat installation preserves flow IDs, and inspect Home, Your Steps, every venture card, a dry-run, and run history with screenshots.

## Test results

- Block checks: 49 passed: connectors 11, customer 10, deadlines 6, feeds 9, filer 3, mail 4, reader 3, rules 3. Reader benchmark: 100% agreement, 100% labeled-value accuracy over 7 fields. See [block log](I3-block-tests.log).
- Venture suite: 163 passed, 3 subtests passed, 2 failed. One failure is `RecallMatcherAcceptanceTests.test_clean_item_uses_required_source_and_date_vocabulary`: the test expects “no match in” while the venture spec and implementation use “no match found in”. The other is `InstallAllTests.test_discovery_is_data_driven_and_only_filters_by_slug`: it assumes there are only Apify flows, while the integrated repository has 31. These checks remain unchanged. See [venture log](I3-venture-tests.log).
- Full backend: 828 passed, 1 skipped, 3 failed, 5 warnings in 868.68 seconds, using `/home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q tests` from `glacier/backend`. The failures are the manual email-trigger template, missing `EMAIL_APP_PASSWORD` for the email-search template, and a local-data-pipeline structured AI response that was not valid JSON. See [backend log](I3-backend-tests.log).
- Focused backend integration after the final Home queue fix: `tests/test_ventures.py`, 7 passed, 1 warning.
- Full UI: `GLACIER_PYTHON=/home/glacier/w/glacier-lean/.venv/bin/python npm run check:ui` from `glacier/web`, via `heavy`; final fresh run passed 30/30 board steps, including the real-backend Messenger event and venture Home checks. First full attempt saw one transient Messenger event assertion; the fresh full run passed. See [UI board log](I3-ui-check-ui.log).
- Venture UI focus check after the Home queue fix: `npm run build && node e2e/ventures.spec.mjs`, all 15 assertions passed.

## Live installation and owner walkthrough

- `npm run live` plus `ventures/install_all.py` installed 31 flows and 12 schedules into a disposable Glacier home. Two repeat installs each reported 31 unchanged and 0 saved; flow IDs stayed identical. Every schedule sets missed-run to `run_once` and overlap to `skip`. See [installer evidence](installer-idempotence.json).
- Each of 11 installed ventures was opened in the real screen and its main flow was dry-run. Results: 2 done, 9 waiting at an owner approval, 0 failed. Home, needs-you, the Your Steps inbox, all 11 cards, all 11 run views, and all 11 history views are captured as 36 `final-*.png` files.
- The grouped secrets step asks for all keys together in Your Steps; values are stored locally and not echoed into the screen or audit. Outbound/filing actions stay at approval steps. The Home needs-you queue includes venture setup and approvals, and Home shows one combined daily digest.
- Live Codex check created `hello.txt`, but the following read step hit the setup script's nested `${GLACIER_HOME:-...}` workspace-path issue. The script was left unchanged. No live owner account keys were available, so government feeds and paid-account reads were not treated as verified. Narrative daily report files per venture were not verified; cards show daily run/status counts.

## Remaining disposition

- PH12.22 remains `in_progress` because PH5 has not exited and release evidence/owner setup remains. No checkpoint was marked done.
- The two venture-suite failures and three backend-suite failures above remain open. The live Codex workspace-path issue, government feed rechecks, connected-account setup, and per-venture narrative daily reports also remain.
- The core sandbox wrapper's embedded browser check had an auth mismatch; its output is retained in [prior core board log](I3-core-board-prior.log). The final full UI board was run separately with the project interpreter and passed.
