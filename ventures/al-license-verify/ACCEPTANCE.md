# al-license-verify acceptance

Match only exact normalized license numbers or names in authorized dated
customer CSVs. Duplicate, stale, missing-field or malformed rows must not produce
confident legal conclusions. Distinct Unicode names cannot collapse into one key.
No-match must refer to the roster's as-of date. Mock the actual Actor boundary to
prove completed lookups charge once only when enabled and uncertain/outage/429
results never charge. Run no real Actor. Board export/commercial permission remains
an owner prerequisite; a CSV fixture is not proof an official export exists.

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

The roster fixture is an authorized, synthetic CSV export-shaped sample, not a
claim that the board offers a downloadable CSV. Its fields `License Number`,
`Name`, `Status`, `Expiration Date`, and `Specialty` correspond to fields shown
on the Alabama Licensing Board for General Contractors' [official license
detail page](https://genconbd.alabama.gov/DATABASE-SQL/detail.aspx?licenseno=S-51389).
The board says its search data is as of a stated date and may be incomplete or
not official; therefore a local `roster_as_of` date and source URL are required
metadata, and no-match is only a result about that dated supplied roster.
`checked_at`, submitted queries, and `business_name` are local input/output
fields, not board data.
