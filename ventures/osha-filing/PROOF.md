# OSHA filing preparation proof

This card makes the OSHA venture more launch-ready, but it is not live with customers. No customer records or accounts, payment, OSHA portal, signature, filing, mail, listing publication, or public outreach were used. The real-backend walkthrough used only the synthetic fixtures in this folder.

## Drift check

- Checkpoint: PH12.16, OSHA filing (V-OSHA3; owner-authorized PH12 wave 6).
- Dependencies: PH5 and PH9 have not reached their exits. PH12 is explicitly parallel-safe for this wave, so work may proceed; this card does not mark the checkpoint or phase complete.
- Defining properties and metrics: P-CONTROL / M-VERIFIED for the customer-held certification and submission gates; P-VERIFY / M-VERIFIED for the totals and source screening; P-USABLE / M-INTERVENE for the reusable CSV template and two owner launch steps.
- Existing tools: the shared OSHA feed adapter, rules checker, deadline tracker, local-only filer guard, and Glacier approval nodes already exist. This card composes them and adds no dependency.
- Acceptance test, written first: `ventures/osha-filing/tests/test_osha_filing.py` imports a synthetic injury-log CSV into a worksheet, screens a synthetic ITA CSV through the CLI while retaining uncertain records, verifies the Jan 2–Mar 2 submission dates and Feb 1–Apr 30 posting dates, and checks the approval graph leaves certification and filing to the customer.

## Verification

Focused acceptance suite:

```text
$ ~/w/glacier-lean/.venv/bin/python -m pytest ventures/osha-filing -q
.............                                                            [100%]
13 passed
```

Manifest/flow validation:

```text
$ ~/w/glacier-lean/.venv/bin/python ventures/install_all.py --only osha-filing --dry-run
4 flows validated: january-outreach, prepare-300a, osha-daily-deadlines, jobber-channel
```

The command-line fixture screen reported `source_mode=synthetic_fixture`, 2 candidates, and 2 uncertain rows. The worksheet CLI test loaded `fixtures/injury-log.example.csv`, calculated two cases and their day totals, and wrote a printable review worksheet. The zero-injury template fixture also parsed with zero cases. These are fixture results, not OSHA source data.

Real local Glacier backend walkthrough:

- Started the FastAPI/DBOS backend with a disposable `GLACIER_HOME` using the project venv.
- Installed all four OSHA flows through `ventures/install_all.py --only osha-filing`.
- Ran `prepare-300a` from Glacier with the synthetic injury-log CSV. After the fixture-input and first-five review approvals, the run reached the `customer_review` approval with the worksheet present, containing the fixture establishment and the customer-only certification/submission language. Run ID: `c64f27bbafb2`.
- This verified the preparation and handoff path. The customer-review approval was left waiting; no signing, posting, or ITA submission occurred.
- A first run exposed two stale approval-edge labels and a step cap below the flow's node count. The flow fixture test caught those conditions; labels now follow the runner's `yes` branch and the cap covers the full path.
- `npm run live` started the real backend and health check, then exited because this worktree's installed web dependencies do not contain `glacier/web/node_modules/vite/bin/vite.js`. The backend was then exercised directly. No UI browser run was possible in this worktree.

Current OSHA public feed check:

```text
$ GLACIER_HOME=/tmp/gf-v-osha3-live-ita ~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py sync
{"alerts": ["Feed sync alert (osha_ita): HTTPError: HTTP Error 403: Forbidden"], "changed": false, "rows": 0}
```

The download was not reachable from this client, so this card does not claim a current live-data screen. The previous PH12.16 proof recorded 400,288 rows in an earlier run; that historical result does not override today's 403. No alternate host or access workaround was used. The included ITA CSV fixture supports local screening until the official public download is reachable.

Other venture suites were run one project at a time with the repository and project directories on `PYTHONPATH`: 12 venture projects passed, with one optional recall-actor live canary skipped. Recall checker has 10 passing tests and one existing wording assertion failure already recorded in `vault/claims/2026-10-10-ph12-12-recall-output-vocabulary.md`; no other venture files were changed. A single root-level `pytest ventures -q` also has import collisions for recall-actor and utility-audits, so it is not used as the per-venture result above.

## Limits and owner actions

- OSHA public feed synchronization is blocked by HTTP 403 in this run; prospect screening has fixture evidence only.
- The ITA prospect fixture is synthetic and cannot be treated as a current lead list. OSHA's [ITA page](https://www.osha.gov/itadata) remains the source for the official download.
- OSHA's [calendar](https://www.osha.gov/calendar) confirms the Feb 1–Apr 30 posting period and Mar 2 submission deadline; OSHA's [recordkeeping FAQ](https://www.osha.gov/injuryreporting/faqs) describes the Jan 2 submission opening. OSHA rules and coverage can change; the customer checks current requirements.
- The HTML output is a review worksheet, not the official Form 300A. CSV input requires one row per distinct recordable case, consistent establishment fields, and a single explicit zero-injury row when appropriate.
- The owner still creates the Jobber app/test account, saves secrets, reviews the first postcard and listing, and manually publishes a marketplace listing if desired. The owner also reviews the first five prepared packets.
- Each establishment's executive checks the worksheet against source records, certifies and signs it, posts it February 1–April 30, and submits required data in its own OSHA ITA account by March 2. Glacier never performs these acts.
- Lob remains render-only; no live address verification or mailing was attempted. No customer checkout, OSHA credentials, or real prospect data were used.
- PH12.16 remains `todo` in NORTHSTAR; this card does not update the checkpoint status or evidence.
