# Warranty registration

This venture prepares HVAC warranty intake records for contractor review. It reads completed Jobber jobs through the shared read-only connector, maps account-labeled text fields for brand/model/serial/install date, calculates registration deadlines, and builds a local review queue plus homeowner email drafts. Drafts are never sent. A `match` is not a legal conclusion or proof of warranty coverage.

## What is ready

The local rules use source-backed eligible-product windows for Trane, Goodman, Daikin, Lennox, and Carrier. California and Quebec are skipped; Lennox units in Florida or Georgia installed on or after January 1, 2026 are also skipped. Rheem/Ruud's reviewed public sources do not establish a universal registration window, so no deadline is calculated for that family. These are intake rules only. Product eligibility and warranty coverage remain the contractor/homeowner's call.

Official registration and serial guidance for Carrier/Bryant, Trane/American Standard, Lennox, Rheem/Ruud, Goodman/Amana, and Daikin is stored in [`brands/`](brands/). Where a rule or serial pattern is not stated clearly, it remains `uncertain - please check`; no serial pattern is enabled. Unknown or unconfirmed unit data remains held for human review.

The synthetic five-job Jobber-shaped fixture has run through the real Glacier engine. It produced five local queue records, five held `uncertain — please check` assessments, and five unsent homeowner drafts. This proves local workflow behavior, not a live Jobber account. The full evidence and limits are in [`PROOF.md`](PROOF.md).

## Jobber setup and owner action

The only current owner setup is one Jobber setup session. The exact clicks, field names, types, blank defaults, and sample formats are pre-written in [`JOBBER-SETUP.md`](JOBBER-SETUP.md); the concise checklist is [`OWNER-STEPS.md`](OWNER-STEPS.md). The reader requests only GraphQL data and does not change Jobber jobs.

Jobber's GraphiQL-issued access token is a temporary test credential that expires after 60 minutes. It can support a short read-only connection check, but it does not prove an always-on live connection. Production OAuth, a published Jobber Marketplace app, and billing are not enabled by this venture. No app is to be published in this setup step.

The local pending deadline input is written to `GLACIER_HOME/ventures/warranty/pending-units.json` (or `~/.glacier/...`). It contains Jobber customer data and stays on the local machine. Credentials are read from Glacier's OS keychain and are not printed.

## Manufacturer terms and permission boundary

The official pages reviewed on 2026-10-11 do not establish permission for an outside service to prepare registrations for a contractor. Daikin's site terms expressly prohibit automated systems from monitoring or copying the sites. Trane's website terms restrict automated page monitoring/copying without prior written permission. Other reviewed materials either address their own sites generally or do not specify third-party preparation. The scope of those terms for a contractor's manual portal visit or local Jobber-only intake remains unconfirmed; those items stay `uncertain - please check`. This is a factual summary, not a legal conclusion.

No owner terms review is needed for the current workflow: it reads Jobber and prepares records locally without accessing manufacturer sites. Before future portal access or registration preparation is added, require documented permission covering that proposed action and customer authorization; until then, keep portal automation disabled. See [Daikin terms](https://daikincomfort.com/terms-of-use), [Trane website terms](https://www.trane.com/content/dam/Trane/Commercial/global/terms-and-conditions-of-use.pdf), [Carrier terms](https://www.carrier.com/us/en/terms-of-use/), and [Goodman legal terms](https://www.goodmanmfg.com/legal), plus the source links in each brand record.

## Local intake check

Create a JSON file containing normalized records with `job_id`, `completed`, `brand`, `model_reading`, `model_confirmation`, `serial_reading`, `serial_confirmation`, `installed_on`, `region`, `homeowner_name`, and `homeowner_email`. Do not put portal passwords in this file. Evaluate it with:

```sh
~/w/glacier-lean/.venv/bin/python -m ventures.warranty.scripts.warranty evaluate --input ./install-records.json --as-of 2026-10-10
```

The opt-in missing-photo output is a draft only. This venture does not send texts or emails, submit portal forms, or automate manufacturer portals.

## Status

**Ready for local, read-only Jobber intake preparation and review.** Live account behavior remains unverified until the owner runs a check with a test account; the temporary GraphiQL token only proves a short-lived connection. This venture depends on contractor customers, so no cold outreach work is added.

Paid billing is not enabled. Stripe or Jobber billing needs separate owner approval.
