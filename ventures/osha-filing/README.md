# OSHA filing preparation — ready for owner setup

Glacier prepares a review worksheet for OSHA Form 300A from the establishment's injury-log CSV. The customer compares every figure with its OSHA 300 Log and hours/headcount records. The executive signs and dates the form, posts it at the establishment from February 1 through April 30, and submits required data through the customer's own OSHA ITA account by March 2 (submission opens January 2). Glacier never certifies or submits a government filing.

## Public data and outreach

The venture refreshes the OSHA ITA establishment summary through the shared `osha_ita` feed and uses it only to screen prospects. The public summary's `size` field records the largest employee-size category reached during the year (code `3` for 250+, codes `2`, `21`, or `22` for 20–249); this is the screening input, rather than annual average employees. Establishments with 20–249 employees are retained only when their industry code matches OSHA's currently published designated-industry table. Missing or ambiguous fields remain `uncertain — please check`. A prospect match is only a lead signal, not an OSHA coverage or compliance determination; OSHA notes that the public data can include establishments that were not required to submit. The industry table is based on OSHA's [published NAICS list](https://www.osha.gov/recordkeeping/naics-codes-electronic-submission) and must be rechecked if that page changes. The current bulk download is linked from OSHA's [ITA data page](https://www.osha.gov/itadata); this client's live request returned HTTP 403, so the current-file canary is still an owner setup step. A saved official CSV can be screened locally with `--source-csv`; `fixtures/ita-establishments.example.csv` remains synthetic and is never represented as current OSHA data.

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

If the live feed remains unavailable, screen a CSV downloaded from OSHA's official ITA data page and record its row count and establishment-ID canary:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prospects --source-csv ./2025_summary_data.csv --as-of 2027-01-03
```

The local-file mode records only the source filename, row count, identifier-canary result, and prospect totals in `prospect-status.json`; it saves at most one minimum-field candidate for proof review. Confirm the file came from OSHA before using it. No alternate host or access workaround is used.

Checkout is not enabled until an owner configures the customer block's Stripe test mode. No credentials or live billing configuration are included.

## Your steps

1. **Owner setup and review:** Download the current ITA Summary Data CSV from OSHA's [official data page](https://www.osha.gov/itadata) in a normal browser, then run the local `--source-csv` screen to record the actual row count and establishment-ID canary. The feed request currently returns HTTP 403 to this client, so prospecting remains fixture-only until that is done. Review the first postcard, recipient source, landing page, marketplace listing, and the first five prepared worksheets; publish the Jobber listing yourself only if you choose. The Jobber test app is already connected. Glacier does not send mail or publish listings.

For every customer filing, the establishment's executive compares the worksheet to source records, certifies and signs it, posts the signed summary February 1–April 30, and submits required data in the customer's OSHA ITA account by March 2. OSHA says submission opens January 2. The annual local reminders prompt those owner/customer actions; they do not sign, post, or submit.
