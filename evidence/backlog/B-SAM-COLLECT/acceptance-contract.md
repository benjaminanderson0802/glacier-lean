# B-SAM-COLLECT — acceptance contract

**Checkpoint:** PH12.5, shared block: government data feeds + deadline tracker.

**Drift check:** This contract advances PH12.5. PH12 depends on PH5 and PH9, both still marked `in_progress` in NORTHSTAR; the PH12 wave explicitly authorizes cards to start before dependencies reach exit, but this contract does not mark a checkpoint done. It serves P-SECURE (credential handling), P-CONTROL (auditable provenance), and P-VERIFY (accept only complete verified results); relevant metrics are M-SECURITY and M-VERIFIED. Existing generic web/search nodes do not establish the SAM.gov API v2 query, secret, pagination, and completeness guarantees below, so this is a connector-specific acceptance contract. The acceptance checks are the fixture cases below, written before feature work. No implementation or test suite was inspected for this contract.

## Contract

Implement a **read-only, bounded snapshot** intake from the official SAM.gov API v2 opportunities search for explicitly selected NAICS code(s). Do not create, update, or submit anything to SAM.gov.

- Read the API key only from Glacier Secrets at run time. Never ask for it in ordinary flow inputs, store it in a flow, snapshot, log, error, or provenance URL, or expose it to downstream steps. Redact it from all diagnostics.
- Make the requested NAICS scope visible and preserve it in snapshot metadata. Any additional search filters that affect the result set must also be recorded.
- Follow every successful result page until the API indicates there are no more results. A snapshot is complete only when every page in that query was accepted and the provider’s end-of-results condition was reached within the configured page/record bounds. A bound reached before that condition is truncation, not success.
- Persist and expose a snapshot as `complete` only after the entire query succeeds. On quota/rate-limit errors, malformed or partial responses, failed pages, or a bound reached before completion, fail the run and leave no saved complete snapshot or downstream-usable partial snapshot.
- Record provenance with the official source URL (credential-free; redact API-key and other secret parameters), the exact query scope, retrieval timestamp in UTC, and retrieval date in UTC. Include record count and pages fetched so completeness is inspectable.
- If the key is missing, stop before any request and explain in plain language that a SAM.gov API key is required, that it must be saved in Glacier Settings → Secrets, and that the run can be retried after saving it. Do not suggest pasting it into a flow or chat.

## Observable fixture acceptance cases

Run these offline against a fake SAM.gov API; no live credentials or network calls are required.

| Fixture | Expected observable result |
|---|---|
| Successful multipage response: two or more pages, with the final page explicitly ending the result set | One complete snapshot contains every fixture record exactly once; page requests follow the API pagination fields; metadata records the selected NAICS scope, UTC retrieval timestamp/date, credential-free official source URL, page count, and record count. |
| Quota/rate-limit response on the first or a later page | Run fails with a quota-specific actionable error; no complete snapshot is saved or exposed to downstream steps, including when earlier pages succeeded. Secret remains absent from error/log output. |
| Partial response: a page has an incomplete/invalid result envelope or cannot be decoded | Run fails as a partial response; no complete snapshot is saved or exposed downstream, even if preceding pages succeeded. Secret remains absent from error/log output. |
| Truncation: configured page/record bound is reached while the API still reports more results (or a page is missing/invalid) | Run fails as incomplete/truncated; no complete snapshot is saved or exposed downstream. It must not silently label the partial records complete. |
| Missing Glacier secret | No API request is made; run fails with the plain-language guidance specified above; no snapshot is saved. |
| Output metadata inspection for a successful snapshot | Snapshot includes selected NAICS and all result-affecting filters, retrieval timestamp and date in UTC, credential-free source URL, complete status, page count, and record count; fixture API key is absent from snapshot content, metadata, logs, and errors. |

Acceptance passes only when every fixture case has these observable outcomes. A failed retrieval must not be represented as an empty successful snapshot.
