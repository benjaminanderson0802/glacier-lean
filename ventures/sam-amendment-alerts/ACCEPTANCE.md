# sam-amendment-alerts acceptance

Compare complete, dated API v2 snapshots by notice ID and NAICS. Detect new
notices and deadline differences without inventing cancellations or historical
amendments. Incomplete pagination, malformed rows and absent dates must be rejected
or explicitly uncertain. Links must identify the particular notice. A source outage
or 429 cannot be rendered as a successful no-change digest or billed. Two buyers,
a working authorized feed and real snapshot coverage precede manual invoicing.

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

The synthetic `opportunitiesData` entries use SAM.gov Get Opportunities Public
API v2 fields `noticeId` (identifier), `title`, `solicitationNumber`,
`naicsCode`, `responseDeadLine` (the documented response spelling; GSA's field
table also contains a typo), `uiLink`, and `links[{rel,href}]`. Its response
envelope uses `totalRecords`, `limit`, and `offset`. GSA documents these fields,
the API key requirement, daily active-record updates, pagination and the
latest-active-version limitation in the [official API specification](https://open.gsa.gov/api/get-opportunities-public-api/).
`retrieved_at`, `source_url`, and the selected NAICS set are local snapshot
metadata/filter settings, not response fields. A snapshot is complete only if
the locally recorded page coverage accounts for `totalRecords`.
