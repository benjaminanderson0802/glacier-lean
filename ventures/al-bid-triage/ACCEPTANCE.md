# al-bid-triage acceptance

Filter customer-transcribed notices by county and trade; exclude expired
notices and collapse identical duplicates. Conflicting duplicates require review,
not arbitrary first-row selection. Missing deadline/issuer/prebid details remain
uncertain. Preserve Unicode, provenance and controlling links. Reject malformed
input. Source outages/429 at the upstream manual collection step cannot be passed
as an empty successful collection. Three firms and useful sample acceptance precede
manual billing. No automated notice collection, bidding or sending.

## Independent tester plan / drift check

Owner Benjamin approved T-PILOTS on 2026-10-10. This advances PH12.22,
P-VERIFY and P-CONTROL, and M-FALSE-DONE, M-VERIFIED and M-AUDIT.
PH5/PH9 remain in_progress; assigned-card authorization permits this audit,
not a phase completion claim. Use existing pytest and Python standard-library
fixtures; no new service or dependency. These criteria precede new tests.
The tester did not build the product and will not change it or its existing tests.

## Shared acceptance rules

- Synthetic values must use documented source fields, types and envelopes.
  Customer mapping fields must be identified as local, never called official API fields.
- Empty input is distinct from missing, malformed, unavailable, rate-limited or
  incomplete input. Such uncertainty must not become a confident negative.
- Customer-visible uncertain results use `uncertain — please check` (an ASCII
  hyphen is also accepted). Valid negative results name the source and date.
- Source-outage-only results never cause a charge. Manual pilot invoices require
  owner action and the kit's buyer acceptance gates. No test sends, publishes,
  registers, pays, or uses a live charging SDK.
- Preserve Unicode names and identifiers. Do not infer absent facts.
- Audit every prospects row for official provenance and business-only contact
  routes. Reachability alone is not proof of a current contact or buyer fit.
- `RUN_LIVE=1` enables read-only public-document/contact canaries. Account-data
  canaries require already configured credentials; skips must say why. No
  automated Alabama notice/license extraction. Public-doc checks do not prove
  authenticated production delivery. Live failures remain failures, never xfail.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q tests/acceptance` from
this kit; prefix `RUN_LIVE=1` for canaries. Evidence and limitations are recorded
in `TEST-FINDINGS.md` and `tests/acceptance/evidence/`.

## Source field provenance

Alabama Builds publishes advertisements as human-readable notices and attached
documents, not as a documented CSV/API schema. The live page is the [official
Advertisements for Bids listing](https://alabamabuilds.gov/AdvertisementBids);
an [official sample notice](https://alabamabuilds.gov/AdvertisementBids/DownloadFile?AdvertisementId=132)
contains project, advertising body, bid due and pre-bid information in prose.
Every `notice_number`, `project`, `advertising_agency`, `county`,
`municipality`, `bid_date`, `prebid_meeting`, `description`, and `official_url`
column in this fixture is therefore a customer/transcriber mapping, not an
official structured field. `source_mode` and `received_at` are local audit
metadata. Tests must not imply automated extraction or source-provided CSV
semantics.
