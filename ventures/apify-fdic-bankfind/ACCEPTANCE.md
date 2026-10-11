# Independent acceptance: apify-fdic-bankfind

Independent tester: T-APIFY3, owner-approved 2026-10-10. Product code is read-only.

Drift check / plan: advances PH12.10 and PH12.22; PH5 and PH9 remain marked
in progress, so no phase exit is asserted. The assigned card authorizes this
parallel-safe audit. Serves P-VERIFY/P-CONTROL, M-FALSE-DONE/M-VERIFIED and
M-AUDIT. Reuse pytest, requests and the installed Apify SDK (I-01); custom code
is limited to independent fixtures/assertions. These criteria precede the tests;
no builder checks are changed (I-03/I-04).

Common acceptance criteria:

- Preserve official identities, source URL, retrieval time, source date and hash.
  Never infer safety, compliance, licensure or credentials from a public record.
- Empty, malformed, unavailable, rate-limited or incomplete sources must not
  masquerade as successful negative findings. Confirmed empty queries are free.
- Customer-visible output uses `match`, `no match found in [sources] as of [date]`,
  or `uncertain - please check` (the spec's em dash is also accepted). Internal
  outcome enums may remain unchanged; a customer-visible message must carry the
  required wording. An unknown optional field may remain null with a warning.
- Only validated successful records are eligible for the documented custom event.
  Outage-only and uncertain results generate zero charge calls. Write the result
  before charging; honor the spending limit and stable run-scoped idempotency.
- Local runs make no payments or external writes. Publishing, account creation,
  payout setup and legal decisions remain owner-only. All network tests restrict
  traffic to GETs on the named official source, without Apify credentials;
  cloud billing tests use an in-memory actor double only.
- Retry 429/503 at most once for a short numeric Retry-After; do not retry a long
  or HTTP-date delay. Space requests >=1 second, cap responses at 5 MB, set
  connect/read timeouts and refuse redirects.
- Construct the UI example from every property `prefill`, falling back to
  `default`, as specified by [Apify input schema v1](https://docs.apify.com/actors/development/actor-definition/input-schema/specification/v1).
  Run the actual `src.__main__` -> Actor main -> real local SDK -> dataset path,
  once with captured HTTP fixtures and once with live sources under RUN_LIVE=1.
  Assert expected identities and real source-backed values, not just exit code.

Run from the repo root using `~/w/glacier-lean/.venv/bin/python -m pytest -q
ventures/apify-fdic-bankfind/tests/acceptance`; set `RUN_LIVE=1` to include the live canary.
Evidence and failures are recorded in this folder's `evidence/acceptance-*`
and `TEST-FINDINGS.md`. Live source outages fail the live canary, never xfail.
No Glacier backend or screen behavior changes; the real runtime under test is
this standalone Actor and its local SDK, not the unrelated Glacier API server.

- Certificate/state/active filters must select the requested institutions.
  Keep certificate/ZIP as strings, convert DATEUPDT to ISO, retain literal ACTIVE.
- Page through a stable source snapshot without duplicate IDs. Honor max_records,
  mark truncation, reject changed vintage or total and discard partial paid results
  after a later-page outage. Optional missing ZIP/date/website remain null.
- Preserve Unicode names and cities without following bank website links.

Fixture field citations: [FDIC institution definitions](https://api.fdic.gov/banks/docs/institution_properties.yaml)
defines `data`, `CERT` (certificate), `NAME`, `ACTIVE` (0/1), `STALP`, `CITY`,
`ZIP`, `DATEUPDT` (source update), `WEBADDR`, `ID` and envelope `score`.
[FDIC OpenAPI](https://api.fdic.gov/banks/docs/swagger.yaml) documents `meta.total`,
`meta.parameters` (filters, fields, limit, offset), `meta.index.name`,
`meta.index.createTimestamp`, outer `data`, and `totals.count`.
[Query documentation](https://api.fdic.gov/banks/docs/) defines filter syntax,
field selection and sorting/paging parameters. `institution.json` is an unedited
response for CERT 3510 with selected fields; provenance records the exact URL
and SHA-256. Mutations retain this nested `data[].data` envelope.
