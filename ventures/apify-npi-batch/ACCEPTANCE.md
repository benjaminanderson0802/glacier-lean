# Independent acceptance: apify-npi-batch

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
ventures/apify-npi-batch/tests/acceptance`; set `RUN_LIVE=1` to include the live canary.
Evidence and failures are recorded in this folder's `evidence/acceptance-*`
and `TEST-FINDINGS.md`. Live source outages fail the live canary, never xfail.
No Glacier backend or screen behavior changes; the real runtime under test is
this standalone Actor and its local SDK, not the unrelated Glacier API server.

- Reject malformed/checksum-invalid NPIs before traffic; deduplicate batches.
  Match exact registry identity, preserve organization/individual Unicode names,
  select LOCATION rather than MAILING, and select the unique primary taxonomy.
- An explicit zero result count is a free negative finding; error envelopes,
  mismatched identities/counts and missing required name/status are uncertain.
- Missing practice address or unique primary taxonomy stays null with warnings.
  One failed NPI does not erase valid independent results elsewhere in the batch.
- Exclude phone/fax, authorized officials and unrelated identifiers from output;
  never contact a provider or imply that registry presence establishes credentials.

Fixture field citations: [CMS API documentation](https://npiregistry.cms.hhs.gov/api-page)
and [official JSON conversion map](https://npiregistry.cms.hhs.gov/help-api/json-conversion)
document `number`, `enumeration_type`; `basic.organization_name`, `first_name`,
`middle_name`, `last_name`, `enumeration_date`, `last_updated`, `status`,
`organizational_subpart`, `certification_date`; `basic.authorized_official_`
`first_name`, `last_name`, `name_prefix`, `name_suffix`, `telephone_number`,
`title_or_position`; `addresses[].address_1`, `address_2`, `address_purpose`,
`address_type`, `city`, `state`, `postal_code`, `country_code`, `country_name`,
`telephone_number`; `taxonomies[].code`, `desc`, `license`, `primary`, `state`,
`taxonomy_group`; `created_epoch` and `last_updated_epoch` (millisecond strings).
The [official v2.1 response](https://npiregistry.cms.hhs.gov/api/?version=2.1&number=1881018208)
provides the `result_count`/`results` envelope and empty arrays `endpoints`,
`identifiers`, `other_names`, `practiceLocations` in the captured provider fixture.
The fixture is unedited; provenance records exact URL/hash. CMS's docs are a
JavaScript app; the field map was inspected in its served main bundle as well.
Artificial mutations are labeled in tests; no synthetic provider is asserted real.
