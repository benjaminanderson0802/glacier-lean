# OSHA filing preparation

Glacier prepares a review copy of OSHA Form 300A from information the establishment provides. The customer compares every figure with its OSHA 300 Log and hours/headcount records. The executive signs and dates the form, posts it at the establishment from February 1 through April 30, and submits the required data through the customer's own OSHA ITA account. Glacier never certifies or submits a government filing.

## Public data and outreach

The venture refreshes the OSHA ITA establishment summary through the shared `osha_ita` feed and uses it only to find repeat filers. An establishment with 250 or more employees is a candidate. An establishment with 20–249 employees is retained only when its industry code matches OSHA's currently published designated industry prefixes. Missing or ambiguous fields remain `uncertain — please check`; this is a prospecting aid, not a legal coverage decision. The prefix list in the script is based on OSHA's [designated industry list](https://www.osha.gov/recordkeeping/naics-codes-electronic-submission) and must be rechecked if that page changes.

The January mail flow produces render-only postcard proofs and a separate page populated with the establishment's source data. The sender is named clearly and the design does not imitate OSHA. No real postcard is sent. The mail block uses Lob test mode only after an owner configures a test key and approval; no live key is accepted by the shared block. The venture does not send messages through Jobber. Its Jobber channel uses the shared read-only connector to preview candidate shops.

The printable HTML review draft is an equivalent preparation aid, not an official OSHA form. The customer can use OSHA's [Form 300A and instructions](https://www.osha.gov/recordkeeping/forms) and [Injury Tracking Application](https://www.osha.gov/injuryreporting/) for the official form and customer submission. Data checks include the sum of the four case categories and a broad hours/headcount plausibility bound; they do not decide whether an establishment is legally covered.

The customer supplies the establishment address and industry code, filing year, average employee count, total hours worked, case-category totals, days away/restriction totals, and executive name/title. A zero-injury confirmation uses zero for every case and day total. `fixtures/300a.zero-injury.example.json` shows the expected local JSON shape; it is synthetic and must not be submitted as real data.

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

Check the current public-data prospect list:

```sh
~/w/glacier-lean/.venv/bin/python ventures/osha-filing/scripts/osha_filing.py prospects
```

Checkout is not enabled until an owner configures the customer block's Stripe test mode. No credentials or live billing configuration are included.

## Your steps

1. Connect the owner's Jobber test account through Glacier Settings → Secrets and review the first postcard design, recipient source, and landing page. Mailing stays render-only.
2. Review the totals and industry-plausibility checks on the first five prepared packets.
3. Compare each Form 300A draft with your records; the executive signs, posts, and submits through the establishment's OSHA ITA account.
