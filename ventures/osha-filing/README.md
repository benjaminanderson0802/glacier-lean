# OSHA filing preparation

Glacier prepares a review worksheet for OSHA Form 300A from the establishment's injury-log CSV. The customer compares every figure with its OSHA 300 Log and hours/headcount records. The executive signs and dates the form, posts it at the establishment from February 1 through April 30, and submits required data through the customer's own OSHA ITA account by March 2 (submission opens January 2). Glacier never certifies or submits a government filing.

## Public data and outreach

The venture refreshes the OSHA ITA establishment summary through the shared `osha_ita` feed and uses it only to screen prospects. An establishment with 250 or more employees is a candidate. An establishment with 20–249 employees is retained only when its industry code matches OSHA's currently published designated industry prefixes. Missing or ambiguous fields remain `uncertain — please check`; this is a prospecting aid, not a legal coverage decision. The prefix list in the script is based on OSHA's [designated industry list](https://www.osha.gov/recordkeeping/naics-codes-electronic-submission) and must be rechecked if that page changes. If OSHA's public download is unavailable, the fixture under `fixtures/ita-establishments.example.csv` supports a local dry-run; it is synthetic and is never represented as current OSHA data.

The January mail flow produces render-only postcard proofs and a separate page populated with the establishment's source data. The sender is named clearly and the design does not imitate OSHA. No real postcard is sent. The mail block uses Lob test mode only after an owner configures a test key and approval; no live key is accepted by the shared block. The venture does not send messages through Jobber. Its Jobber channel uses the shared read-only connector to preview candidate shops.

The printable HTML worksheet is an equivalent preparation aid, not an official OSHA form. The customer can use OSHA's [Form 300A and instructions](https://www.osha.gov/recordkeeping/forms) and [Injury Tracking Application](https://www.osha.gov/injuryreporting/) for the official form and customer submission. Data checks include the sum of the four case categories and a broad hours/headcount plausibility bound; they do not decide whether an establishment is legally covered.

The annual dates above follow OSHA's [recordkeeping FAQ](https://www.osha.gov/injuryreporting/faqs) and [calendar](https://www.osha.gov/calendar); customers should check the current instructions for their establishment.

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

Checkout is not enabled until an owner configures the customer block's Stripe test mode. No credentials or live billing configuration are included.

## Your steps

## Owner launch steps

1. Create and connect the owner's Jobber developer/test account in Glacier Settings → Secrets; review the first postcard, recipient source, landing page, and marketplace listing, then submit the listing yourself if you choose to publish it. Glacier does not create accounts or publish listings.
2. Review the totals and industry-plausibility checks on the first five prepared packets.

For every customer filing, the establishment's executive compares the worksheet to source records, certifies and signs it, posts the signed summary February 1–April 30, and submits required data in the customer's OSHA ITA account by March 2. The annual local reminders prompt those owner/customer actions; they do not sign, post, or submit.
