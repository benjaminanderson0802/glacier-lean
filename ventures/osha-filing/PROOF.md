# OSHA filing preparation proof

This file records commands and outputs for the OSHA filing venture. The deliverable is not live: no customer account, real person, mail service, OSHA portal, signature, or payment was contacted or used.

## Drift check

- Checkpoint: PH12.16 (V-OSHA2), owner-approved PH12 wave 6.
- Dependencies: PH5/PH9 are not at exit; the task is explicitly authorized to start in this wave. No phase status is changed here.
- Defining properties and metrics: P-CONTROL and P-VERIFY; M-VERIFIED and M-INTERVENE.
- Existing tools: all required shared blocks exist and are imported. No shared block changes or new dependencies.
- Acceptance test: `ventures/osha-filing/tests/test_osha_filing.py` checks 300A arithmetic, hours plausibility, uncertain missing data, Jan 2–Mar 2 and no duplicate deadline firing, conservative public feed prospect selection, local-only filer guard, and approval/customer-submission flow wiring.

## Verification

Focused acceptance tests:

```text
$ /home/glacier/w/glacier-lean/.venv/bin/python -m pytest -q ventures/osha-filing/tests/test_osha_filing.py
......                                                                   [100%]
6 passed in 0.07s
```

Manifest and flow validation:

```text
$ /home/glacier/w/glacier-lean/.venv/bin/python ventures/install_all.py --only osha-filing --dry-run
4 flows validated: january-outreach, prepare-300a, daily-deadlines, jobber-channel
```

Synthetic zero-injury Form 300A packet:

```text
$ /home/glacier/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prepare-300a --input ventures/osha-filing/fixtures/300a.zero-injury.example.json --output /tmp/osha-300a-review.html
{"result":"match","check_count":8,"signature":"customer_signature_required","submission":"customer_submits_in_osha_ita","printable_draft_created":true}
```

Live public source:

```text
$ /home/glacier/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py sync
{"alerts": [], "changed": false, "rows": 400288}
```

The live feed parser loaded 400,288 rows from OSHA's official ITA download page without a format alert. A real-data prospect run using `--as-of 2027-01-03` found 249,763 candidate records and kept 150,525 records uncertain because the available employee/industry fields did not establish the specified prospect criteria. The preview harness selected one address-complete record, rendered the postcard PDF and distinct landing page, and returned `mail_status=render_only`, `postcard_status=render_only`, `address_verification=uncertain` (no Lob test key configured). No address was mailed or displayed here.

The four flow acceptance commands passed against a disposable local `GLACIER_HOME` with synthetic status files.

The real-Glacier attempt used the required wrapper:

```text
$ heavy npm run live  # from glacier/web
backend startup: succeeded
Vite startup: failed; Node could not find glacier/web/node_modules/vite/bin/vite.js (MODULE_NOT_FOUND)
```

The backend started, then the live runner shut it down when Vite failed. This worktree's `glacier/web/node_modules` is present but lacks Vite. Dependency installation or borrowing another worktree's node_modules is outside this venture's file lane, so I stopped without changing platform or environment files. A real Glacier flow run and screenshot remain unverified; no checkpoint status is changed.

## Limitations

- The high-hazard NAICS prefixes come from OSHA's current designated industry page and should be rechecked if that page changes; missing or unknown industry data is excluded as uncertain.
- Lob address verification and delivery are unavailable without the owner's test key and explicit approval. The venture currently creates render-only proofs.
- The Jobber connector requires an owner-created test account and keychain secrets, and its current read-only schema does not include employee counts; shops stay uncertain until that channel has a verified staff-count source.
- OSHA ITA credentials and customer submissions are deliberately out of scope; no real portal run is attempted.
