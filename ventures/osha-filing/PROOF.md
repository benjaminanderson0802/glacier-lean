# OSHA filing preparation proof

The OSHA venture is **ready for owner setup**, not live with customers. No customer records or accounts, payment, OSHA portal, signature, filing, mail, listing publication, or public outreach were used. The real-backend walkthrough used only the synthetic fixtures in this folder. The current official public CSV still needs to be downloaded by the owner in a normal browser because the local source request returns HTTP 403.

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
...X.............                                                        [100%]
16 passed, 1 xpassed
```

The independent OSHA acceptance file was run with its `xfail` marker ignored:

```text
$ ~/w/glacier-lean/.venv/bin/python -m pytest ventures/osha-filing/tests/acceptance/test_v_osha3.py -q --runxfail
....                                                                     [100%]
4 passed
```

The CSV-to-worksheet case exercised `scripts.filing.prepare_from_injury_log_csv` with the synthetic intake fixture and confirmed that a worksheet file is produced while `signed` and `submitted` remain false and customer certification/submission remains required. The worksheet records missing values for customer confirmation. The whole venture suite then reported `16 passed, 1 xpassed`; the extra pass is an independent guide check whose xfail marker is also now satisfied. All of this is fixture/local evidence.

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

## Release-gate recheck — 2026-10-10

The existing `ventures/osha-filing/tests/test_osha_filing.py` acceptance checks were left unchanged. Five additional venture-owned regression tests now cover the public ITA size field, local CSV row-count/identifier canary reporting, choosing the next filing year for reminders after April, and rendering postcard/landing-page references. The test input for the new CSV case is schema-shaped and synthetic; it is not the official OSHA file.

The current public-source references were checked against OSHA's live pages. OSHA's [ITA data page](https://www.osha.gov/itadata) links the current summary CSV and says records can include establishments that did not have a reporting requirement. OSHA's [summary data dictionary](https://www.osha.gov/sites/default/files/summary_data_dictionary.pdf) defines `size` as the maximum employee-size category reached during the year, separate from `annual_average_employees`; the screener now uses `size` when present (code `3` for 250+, and codes `2`, `21`, or `22` for 20–249). OSHA's [designated-industry table](https://www.osha.gov/recordkeeping/naics-codes-electronic-submission) and [ITA FAQ](https://www.osha.gov/injuryreporting/faqs) support the 20–249 screening rule. This remains lead screening only, not a coverage decision. The [ITA page](https://www.osha.gov/injuryreporting/), [FAQ](https://www.osha.gov/injuryreporting/faqs), and [calendar](https://www.osha.gov/calendar) confirm submission opens January 2, is due March 2, and the signed summary must be posted February 1–April 30. The [recordkeeping forms page](https://www.osha.gov/recordkeeping/forms) provides the official form and explains equivalent formats.

If a downloaded official CSV is available, the new local mode records source filename, row count, establishment-ID canary, candidate count, and uncertain count without exporting the full source file:

```text
$ ~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prospects --source-csv ./2025_summary_data.csv --as-of 2027-01-03
```

This mode was verified with a synthetic schema-shaped CSV only. A fresh public sync in this card still returned HTTP 403, with `changed=false` and `rows=0`; therefore no current public row count or canary is claimed.

The render-only synthetic postcard preview also ran through the venture CLI. It screened four synthetic establishment rows (two candidate signals and two uncertain), saved one minimum-field sample, produced a postcard PDF and a distinct local landing page, and passed the outreach rule check. The printed proof contains the selected fixture establishment name and a clearly labeled local page reference; it contains no unresolved template variables. Address verification remained uncertain because no test key was configured; no mail was sent. The local landing reference is not a hosted URL.

### Real Glacier engine walkthrough

Started FastAPI/DBOS with `GLACIER_HOME=/tmp/gf-rg-osha-20261010` and installed all four OSHA flows using the project venv. The first install saved the four flow records; the repeat install reported all four unchanged.

- `prepare-300a`, run `6e72d02ec1e5`: used `fixtures/injury-log.example.csv` copied to the temporary home's `incoming/injury-log.csv`. The engine approved the synthetic input-ready and first-five review gates, ran `prepare` successfully, and wrote `packets/300a-review.html` (1,986 bytes). All eight worksheet field/arithmetic checks passed; output reported `result=match`, `signature=customer_signature_required`, and `submission=customer_submits_in_osha_ita`. The run stopped at `customer_review`, with the fixture establishment present and the unsigned/certification disclaimer visible. No customer review, signature, posting, or submission was performed.
- `osha-daily-deadlines`, run `136bb6ef71b0`: status `done`; both nodes completed and its independent command check passed. On the 2026-10-10 as-of date, output named the next cycle: ITA window `2027-01-02 through 2027-03-02`, due `2027-03-02`; posting window `2027-02-01 through 2027-04-30`. The due list was empty in October, as expected.

The owner-ready state leaves one setup/review step: download the current official summary CSV in a normal browser, run `--source-csv` to record its real row count and canary, then review the first five worksheets and outreach materials. The Jobber test app is already connected; any marketplace publication remains the owner's choice. Customers still review and complete their own filings. No alternate data host or blocked-request workaround was used. PH12.16 remains `todo` in `NORTHSTAR.yaml`; this card did not change the roadmap checkpoint.

Anti-pattern review: the historical 400,288-row count remains explicitly historical, and no current public-feed result is claimed. The first postcard preview exposed unresolved template values; those are now filled or marked as a local unhosted reference, with a new regression test. Acceptance files were not changed. No status claim is based only on this report; the venture tests, installer check, and engine runs are linked above.

Other venture suites were run one project at a time with the repository and project directories on `PYTHONPATH`: 12 venture projects passed, with one optional recall-actor live canary skipped. Recall checker has 10 passing tests and one existing wording assertion failure already recorded in `vault/claims/2026-10-10-ph12-12-recall-output-vocabulary.md`; no other venture files were changed. A single root-level `pytest ventures -q` also has import collisions for recall-actor and utility-audits, so it is not used as the per-venture result above.

## Limits and owner actions

- OSHA public feed synchronization is blocked by HTTP 403 in this run; prospect screening has fixture evidence only.
- The ITA prospect fixture is synthetic and cannot be treated as a current lead list. OSHA's [ITA page](https://www.osha.gov/itadata) remains the source for the official download.
- OSHA's [calendar](https://www.osha.gov/calendar) confirms the Feb 1–Apr 30 posting period and Mar 2 submission deadline; OSHA's [recordkeeping FAQ](https://www.osha.gov/injuryreporting/faqs) describes the Jan 2 submission opening. OSHA rules and coverage can change; the customer checks current requirements.
- The HTML output is a review worksheet, not the official Form 300A. CSV input requires one row per distinct recordable case, consistent establishment fields, and a single explicit zero-injury row when appropriate.
- The compact single-row intake adapter may produce an incomplete JSON review worksheet so missing fields can be confirmed by the customer; its `uncertain` result is not an OSHA coverage or compliance decision.
- The owner setup/review step is to download the current official OSHA CSV in a normal browser and run the local canary, review the first postcard, listing, and five prepared packets, and publish the marketplace listing only if desired. The Jobber test app is already connected.
- Current tests after this recheck: `~/w/glacier-lean/.venv/bin/python -m pytest ventures/osha-filing -q` → 22 passed; `~/w/glacier-lean/.venv/bin/python -m pytest ventures/tests -q` → 21 passed; installer dry-run → 4 flows validated.
- Each establishment's executive checks the worksheet against source records, certifies and signs it, posts it February 1–April 30, and submits required data in its own OSHA ITA account by March 2. Glacier never performs these acts.
- Lob remains render-only; no live address verification or mailing was attempted. No customer checkout, OSHA credentials, or real prospect data were used.
- PH12.16 remains `todo` in NORTHSTAR; this card does not update the checkpoint status or evidence.
