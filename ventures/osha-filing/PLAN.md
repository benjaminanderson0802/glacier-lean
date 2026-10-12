# P-OSHA implementation plan and drift check

## Drift check

- **Checkpoint:** PH12.16, OSHA filing. This card explicitly authorizes V-OSHA work in wave 6.
- **Dependencies:** PH5 and PH9 remain in progress. PH12 is explicitly authorized for parallel work; this card will not mark PH12.16 done or change the roadmap.
- **Defining properties and metrics:** P-VERIFY / M-VERIFIED (source URL, schema, row-count and establishment-ID canaries; first worksheets remain customer-reviewed), P-CONTROL / M-AUDIT (no signature, submission, or mail), and P-USABLE / M-INTERVENE (automatic first-five drafts, minimal owner review).
- **Existing tools:** Reuse the shared `osha_ita` feed and existing worksheet renderer. The DOL data catalog is free and official, but its OSHA datasets cover enforcement records, not ITA Form 300A summaries; no paid tool or new dependency is needed. OSHA's own data page links directly to the bulk CSV, which the existing adapter already discovers. The direct file currently returns HTTP 403 from this runtime too, so this environment-level block must remain visible in the canary result.
- **Acceptance test, written before implementation:** Unit tests will verify (a) only the official page-linked OSHA summary CSV is selected, (b) a valid CSV with a nonempty unique establishment-ID canary is accepted and missing/duplicate IDs or missing required columns are rejected, (c) unavailable official data is reported as blocked without treating a fixture as live data, and (d) a command creates at most five unsigned source-linked review worksheets from a real/local snapshot, with missing values marked for customer confirmation and no submission or mailing.

## Implementation boundaries

No files under any `tests/acceptance` directory will be modified. No actual mail, listing publication, account action, customer outreach, signature, or OSHA filing will occur. The five worksheets are draft artifacts derived from an explicitly named source snapshot; they are not generated from a synthetic fixture during the live canary.
