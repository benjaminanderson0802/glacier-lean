# job-closeout acceptance

Only completed jobs become local Markdown/PDF packets. Supplied work,
customer, invoice and equipment facts must survive; absent fields stay uncertain.
Reject GraphQL errors, partial pages and invalid completion dates. Both deliverables
must preserve names such as José and 李. A source outage or HTTP 429 produces no
packet and no charge. First five packets require buyer review before the $49 invoice.
Photo placeholders are allowed; embedding and manufacturer registration are excluded.

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

The fixture uses Jobber's official GraphQL Job fields `id` (EncodedId string),
`jobNumber` (integer), `title` (nullable string), `jobStatus` (enum),
`completedAt` (nullable ISO-8601 date-time), `customFields` (union list),
`client.name`, `property.address.city`, `property.address.province`, and
`property.address.postalCode`; the response envelope is GraphQL `data` with
`account.name` and `jobs.nodes/pageInfo`. `extensions.versioning.version` is
Jobber's version metadata. The fixture may add a GraphQL `errors` array, which
must prevent accepting partial data. These shapes are documented in the
[official Jobber API reference](https://developer.getjobber.com/docs/), which
also documents OAuth scopes, version headers, pagination and rate limits.
`business_name`, equipment labels, work summary and invoice reference are
local packet/mapping fields; Jobber custom field values are not standardized
equipment or invoice fields.
