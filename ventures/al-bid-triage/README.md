# Alabama public works bid triage

## What it does

This pilot kit turns notice details a contractor already received into a short weekly list of likely relevant public works bids. The initial test is for general contractors working in Mobile and Baldwin Counties. It shows the issuer, county, due date, pre-bid meeting, source link, and a next step. Missing dates stay marked uncertain. The issuing authority's notice controls.

Alabama Builds is the state's public works notice source, but its listings may be incomplete. The research did not establish permission or a stable API for automated extraction. This kit therefore does not visit Alabama Builds or any other procurement site. A contractor supplies an official notice email, an official download/export, or an official link. The owner verifies that each link is an official source and reviews the generated digest.

The prototype is a local CSV-to-Markdown script. It filters by trade keywords and county, drops expired notices, keeps one copy of each notice number, preserves source links, and flags missing deadlines. It does not register vendors, contact agencies, submit bids, or send the digest.

## Who pays

The proposed buyer is a small or midsize Alabama general contractor that pursues local public works and wants a shorter, source-linked weekly review. The included prospect list is an initial interview/pitch list from the public AGC Mobile member directory, not proof of fit or interest.

## Price hypothesis

Test one 30-day pilot at **$49**, covering one weekly digest for the selected counties. This is a hypothesis, not a market price. A pilot should continue only if at least three firms commit to the paid pilot and a contractor confirms that the digest saves time or surfaces a relevant notice. Official portal search and alerts are free substitutes, so the pilot must demonstrate a meaningful filtering benefit.

## Owner steps

1. Send the pitch in [PILOT.md](PILOT.md) to the selected businesses in [prospects.csv](prospects.csv).

If anyone responds, the owner personally discusses scope and payment. The pilot itself uses notice emails, official exports, or links that the contractor chooses to provide. Customers remain responsible for vendor registration, qualifications, addenda checks, and bids.

## Run locally

```sh
~/w/glacier-lean/.venv/bin/python ventures/al-bid-triage/scripts/bid_triage.py \
  --input path/to/contractor-supplied-notices.csv \
  --trade general-contracting \
  --counties Mobile,Baldwin \
  --as-of 2026-10-10 \
  --output local-digest.md
```

Accepted trades are `general-contracting`, `electrical`, `roofing`, `grading`, and `fencing`. The CSV header and fixture examples are under `tests/fixtures/`. The script makes no network requests. Check any supplied URLs yourself before relying on them.

Run the kit checks with:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/al-bid-triage -q
```

## Source and legal limits

- Alabama Builds public works listings: <https://alabamabuilds.gov/AdvertisementBids>. The research says its listings can be incomplete and did not establish automated extraction rights; no live notice was fetched for the included sample.
- Alabama administrative rule on vendor requirements: <https://admincode.legislature.state.al.us/administrative-code/355-4-1-.03>. Do not register as a vendor on behalf of customers. Keep their profiles and bids under their control.
- Prospects source: AGC Mobile member directory at <https://theconstructioncenter.org/directory/>. Only business contact details published there are included, with no contact-person names.

## Current limits

No real Alabama Builds listing or customer export was available to this card. The sample is generated from synthetic fixture rows with `.example` URLs and is clearly labeled. The prospect list is dated 2026-10-10 and must be checked against the directory before outreach. The pilot has not been sold or validated with buyers.

## Drift check and acceptance

- **Checkpoint:** PH12, Ventures on Glacier; this card advances an owner-approved venture toward the phase exit. ORCHESTRATION does not list this pilot-kit ID as a separate checkpoint.
- **Dependencies:** PH12 depends on PH5 and PH9, and both phase statuses are still `in_progress`. The card may start under the owner-approved PH12 wave, but this work does not mark PH12 complete.
- **Properties and metric:** P-GOALS and P-USABLE (one clear path from a researched idea to a buyer test), P-LOOPS (repeatable notice triage), and P-CONTROL (owner sends all external email and customers keep bid control); relevant metric M-INTERVENE.
- **Existing tools:** Glacier flows already handle local orchestration; free official procurement listings and alerts exist. The custom code is limited to CSV filtering and digest rendering because it must join customer-chosen scope to supplied notices without crawling or paying for data.
- **Acceptance:** `~/w/glacier-lean/.venv/bin/python -m pytest ventures/al-bid-triage -q`; verify `venture.json` against `ventures/venture.schema.json`; validate the flow with `ventures/install_all.py --only al-bid-triage --dry-run`; confirm the one sample names its fixture provenance and the prospects rows link to a public business directory.
