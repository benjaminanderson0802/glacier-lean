# Proof: Louisiana Contractor License Status

## Acceptance check

Three live LSLBC license lookups must return the recorded business names, literal board statuses, expiration dates, direct official detail URLs, and UTC check times. Search and detail requests must be spaced at least one second apart. Incomplete readable details return `uncertain — please check` / `uncertain`; source or malformed-search failures return `uncertain — please check` / `unverifiable`; a readable empty search is a dated no-match. The standalone Apify SDK Actor must emit a source-backed record. Glacier's Louisiana canary flow must validate and pass in a real backend; owner publication approval remains a separate release gate.

## Source choice and live probe

The [LSLBC contractor search page](https://lslbc.louisiana.gov/contractor-search/) links logged-out search by license number and company name. The portal returned HTTP 200 for its page, a keyless number-search POST, and public detail requests. It requires at least three characters for company-name search and caps broad result pages at 1,500 rows. Probe rationale and alternatives are recorded in the [venture proof](../apify-tools/PROOF.md). No credentials, CAPTCHA, proxy, or paid data source were involved.

## Live canaries and source evidence

The official public source used by the adapter is the [Louisiana State Licensing Board of Contractors search portal](https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByNumber), linked from the [LSLBC contractor search page](https://lslbc.louisiana.gov/contractor-search/). The saved canary expectations contain direct official detail-record URLs and their original UTC probe times in [`tests/canaries.json`](tests/canaries.json). This is live-source evidence; it is separate from fixture/local test evidence and does not imply an Actor was published.

The daily canary command:

```sh
GLACIER_HOME=/tmp/apify-la-canary-test \
PYTHONPATH=ventures/apify-tools-louisiana \
~/w/glacier-lean/.venv/bin/python ventures/apify-tools-louisiana/scripts/daily_canary.py
```

returned `status: healthy`, three matching records, and no failed licenses. The exact JSON is in [evidence/live-canary-run.json](evidence/live-canary-run.json); the expected names, statuses, expirations, source URLs, and initial probe timestamps are in [tests/canaries.json](tests/canaries.json).

| License | Business name | Literal status | Expiration |
| --- | --- | --- | --- |
| `CL.00001` | `BROWN & ROOT INDUSTRIAL SERVICES, LLC` | `Active` | `2027-07-31` |
| `CL.68755` | `09 Construction Services, LLC` | `Active` | `2029-07-18` |
| `RL.883684` | `BROWN & ROOT INDUSTRIAL SERVICES, LLC` | `Active` | `2027-09-12` |

## Local tests and Actor run

Command:

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/apify-tools-louisiana -q
```

Result: **9 passed, 3 live canary subtests passed**. The suite covers keyless request construction, source parsing, name filtering, schema shape, no-match/outage/malformed-source states, incomplete records, rate limiting, and canary maintenance behavior.

The standalone Actor ran with Apify SDK 4.1.0 from `ventures/apify-tools-louisiana` using `{"license_number":"CL.68755"}`. It exited `0` and emitted `09 Construction Services, LLC`, status `Active`, expiration `2029-07-18`, and its official record URL. The output is saved in [evidence/local-actor-output.json](evidence/local-actor-output.json). The copied requirements files are identical (SHA-256 `488cf2d4e248cbf8a884ee6436a1ca0f073b265d20cb89bbb3da07b94bebebeb`).

## Independent review and owner-only publication steps

OpenCode `opencode/nemotron-3.5-lightning-free` completed a distinct-engine review of the adapter, tests, schemas, billing configuration, and listing. It found no blocking issues; the review and its limitations are recorded in [REVIEW.md](REVIEW.md). The `apify-tools` installer dry-run validated all four manifest flows, including the Louisiana canary and separate approval flows.

The Louisiana Actor is still a review draft. Its final daily flow run completed in the real Glacier backend with `verified: true` (run `5a0844b62ec4`); full run evidence is saved above. This is the real Glacier canary evidence, not publication evidence.

The remaining steps are owner-only:

1. **Your step — account and deployment:** create/configure the Apify developer and payout account, complete any identity checks, log in with the official pinned CLI, and upload the Actor with `(cd ventures/apify-tools-louisiana && npm exec --yes --package=apify-cli@1.10.0 -- apify push)`.
2. **Your step — approval and publication:** review the distinct-engine result in [`REVIEW.md`](REVIEW.md), confirm pricing and billing limits, run the separate Louisiana Glacier publication approval, then publish this listing yourself in Apify Console. The Mississippi approval cannot be reused.

No account was created, payout or identity setup was completed, CLI upload or publication was performed, or money spent. The Actor remains unpublished until the owner completes both steps.
