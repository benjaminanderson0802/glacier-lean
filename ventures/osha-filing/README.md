# OSHA filing preparation — blocked on official feed access

Glacier prepares a review worksheet for OSHA Form 300A from the establishment's injury-log CSV. The customer compares every figure with its OSHA 300 Log and hours/headcount records. The executive signs and dates the form, posts it at the establishment from February 1 through April 30, and submits required data through the customer's own OSHA ITA account by March 2 (submission opens January 2). Glacier never certifies or submits a government filing.

## Public data and outreach

The venture refreshes the OSHA ITA establishment summary through the shared `osha_ita` feed and uses it only to screen prospects. The public summary's `size` field records the largest employee-size category reached during the year (code `3` for 250+, codes `2`, `21`, or `22` for 20–249); this is the screening input, rather than annual average employees. Establishments with 20–249 employees are retained only when their industry code matches OSHA's currently published designated-industry table. Missing or ambiguous fields remain `uncertain — please check`. A prospect match is only a lead signal, not an OSHA coverage or compliance determination; OSHA notes that the public data can include establishments that were not required to submit. The industry table is based on OSHA's [published NAICS list](https://www.osha.gov/recordkeeping/naics-codes-electronic-submission) and must be rechecked if that page changes. OSHA's [ITA data page](https://www.osha.gov/itadata) links a direct bulk CSV at `https://www.osha.gov/sites/default/largefiles/`; both the page and its direct current CSV returned HTTP 403 to this script client on 2026-10-11. The official [DOL API catalog](https://apiprod.dol.gov/v4/datasets) lists OSHA enforcement datasets but no ITA summary dataset. The adapter only follows the official page's own HTTPS download link, then requires a nonempty unique establishment-ID canary. It does not impersonate a browser or treat a manual download as a live refresh. `fixtures/ita-establishments.example.csv` remains synthetic and is never represented as current OSHA data.

The January mail flow produces render-only postcard proofs and a separate page populated with the establishment's source data. The sender is named clearly and the design does not imitate OSHA. No real postcard is sent. The mail block uses Lob test mode only after an owner configures a test key and approval; no live key is accepted by the shared block. The venture does not send messages through Jobber. Its Jobber channel uses the shared read-only connector to preview candidate shops.

The printable HTML worksheet is an equivalent preparation aid, not an official OSHA form. The customer can use OSHA's [Form 300A and instructions](https://www.osha.gov/recordkeeping/forms) and [Injury Tracking Application](https://www.osha.gov/injuryreporting/) for the official form and customer submission. Data checks include the sum of the four case categories and a broad hours/headcount plausibility bound; they do not decide whether an establishment is legally covered.

The annual dates above follow OSHA's [recordkeeping FAQ](https://www.osha.gov/injuryreporting/faqs) and [calendar](https://www.osha.gov/calendar): submission opens January 2, data is due March 2, and workplace posting runs February 1–April 30. Customers should check the current instructions for their establishment. The [ITA data dictionary](https://www.osha.gov/sites/default/files/summary_data_dictionary.pdf) defines the public `size` field as maximum employee size during the year, separate from annual average employees.

The customer provides its injury log using `templates/customer-injury-log-template.csv`: one row per distinct recordable case, with consistent establishment, employee, hours, and executive details on every row. Use a single `zero_injury` row with a blank case ID when there were no recordable cases. Glacier counts cases by category and adds day totals, then writes the review worksheet; duplicate IDs, unsupported categories, conflicting establishment details, or incomplete day totals are rejected for correction. `fixtures/injury-log.example.csv` and `fixtures/ita-establishments.example.csv` are synthetic E2E fixtures and must not be submitted or treated as OSHA data. Existing JSON input remains supported (`fixtures/300a.zero-injury.example.json`).

The `scripts.filing.prepare_from_injury_log_csv` adapter also accepts the compact single-row summary format used by the local intake workflow. It writes an unsigned JSON worksheet, keeps missing identity and certification values visible for customer confirmation, and schedules a local filing-window reminder. It does not sign, post, or submit.

### Jobber marketplace draft

**Name:** Glacier OSHA Filing Preparation<br>
**Short description:** Prepare and track your annual OSHA Form 300A summary.<br>
**Description:** Glacier prepares a customer-reviewed Form 300A draft and reminders for the annual filing and workplace posting windows. The customer compares the values with its own records, signs and dates the form, posts it, and submits the required data through the customer's own OSHA ITA account. Glacier does not provide legal determinations, certify filings, or submit to OSHA.<br>
**Data and permissions:** Read only the minimum Jobber account and shop details needed for the contractor's selected workflow. No message, job, or customer record writes.<br>
**Owner action:** Create and submit the Jobber listing after reviewing its current marketplace rules. No account creation or app publication is performed by this venture.

## Run locally

Refresh the shared public feed:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py sync
```

Prepare a printable review copy from customer-confirmed JSON:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prepare-300a --input ./300a.json --output ./300a-review.html
```

Or prepare the worksheet from the customer's completed injury-log CSV:

```sh
cp ventures/osha-filing/templates/customer-injury-log-template.csv ./injury-log.csv
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prepare-300a --input ./injury-log.csv --output ./300a-review.html
```

Check the current public-data prospect list:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prospects
```

For an offline synthetic screening walkthrough, use the explicitly labeled fixture mode:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prospects --fixture ventures/osha-filing/fixtures/ita-establishments.example.csv --as-of 2027-01-03
```

Prepare the first five source-linked worksheets automatically after the official feed is restored and passes its canaries:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prepare-first-five
```

The command refreshes the live official feed, refuses a failed or stale source, and writes at most five unsigned HTML review worksheets plus `first-five-status.json` under `$GLACIER_HOME/ventures/osha-filing/worksheets/`. Outside the Jan 2–Mar 2 filing period, it screens against the next upcoming January window so the drafts can be prepared in advance. The worksheets copy public historical summary values and mark missing executive/current-year fields for customer confirmation; they do not determine coverage, mail, sign, or submit. For an explicit local recovery from an official CSV already obtained by an authorized operator, the same command accepts `--source-csv PATH`; the result is labeled `local_official_csv` and still requires the ID canary. This local mode is not represented as a live-feed canary:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prepare-first-five --source-csv ./2025_summary_data.csv --source-url https://www.osha.gov/itadata --as-of 2027-01-03 --output-dir ./osha-review-worksheets
```

The local-file mode records only the source filename, row count, identifier-canary result, and prospect totals in `prospect-status.json`; it saves at most one minimum-field candidate for proof review. Confirm the file came from OSHA before using it. No alternate host or access workaround is used.

Checkout is not enabled until an owner configures the customer block's Stripe test mode. No credentials or live billing configuration are included.

## Outreach and owner steps

This venture depends on written postcard or marketplace outreach; cold outreach is not being expanded. No postcard is sent and no listing is published. The live data source currently blocks this script client, so prospect worksheets are not available yet. See [OWNER-STEPS.md](OWNER-STEPS.md) for the single review action that becomes available after source access is restored. The Jobber test app is already connected.

For every customer filing, the establishment's executive compares the worksheet to source records, certifies and signs it, posts the signed summary February 1–April 30, and submits required data in the customer's OSHA ITA account by March 2. OSHA says submission opens January 2. The annual local reminders prompt those owner/customer actions; they do not sign, post, or submit.
