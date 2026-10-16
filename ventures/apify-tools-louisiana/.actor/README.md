# Louisiana Contractor License Status

Look up Louisiana contractor license status and expiration from public Louisiana State Licensing Board for Contractors records. Search by license number or company name and export source-linked results.

Search Louisiana State Licensing Board for Contractors (LSLBC) public records by license number or business name. Get source-linked JSON with the reported status, expiration date and UTC check time. Use one lookup or a batch of up to 100 queries.

## Use cases

- Add a dated license-record check to subcontractor onboarding.
- Refresh a list of known license numbers for human review.
- Feed source links and expiry fields into a procurement spreadsheet or internal workflow.

This tool reports what the source says; the board remains the authority.

## Input example

```json
{
  "license_number": "CL.68755"
}
```

Use `name` instead of `license_number` for a business-name substring search. Set `max_results` from 1 to 10 (default 1) for name searches. Louisiana names require at least three characters. For batches, use `{"queries": [{"license_number": "CL.68755"}]}`, up to 100 objects. Each object supplies a license number or name. A batch overrides the top-level single query. Do not treat a truncated name search as a complete roster.

## Output example

Recorded local Actor output from 2026-10-11 UTC (October 10 in Alabama); historical example, not a statement of current status.

```json
{
  "outcome": "match",
  "verification_state": "verified",
  "license_number": "CL.68755",
  "business_name": "09 Construction Services, LLC",
  "license_type": "Commercial License Certificate",
  "status": "Active",
  "effective_date": "07/19/2026",
  "expiration_date": "2029-07-18",
  "source_url": "https://arlspublic.lslbc.louisiana.gov/Public/_DisplayOnlineDetails/?key=R6DulTdQAO08c2WY3yqQKg%3d%3d&Source=DetailedSearch",
  "checked_at": "2026-10-11T01:14:40+00:00"
}
```

The default dataset contains one row per returned record, or a dated no-match/uncertain row. Matches include `business_name`, `license_number`, `status`, `expiration_date`, `source_url` and `checked_at`; Louisiana may also include `license_type` and `effective_date`. Export the dataset as JSON or CSV in Apify.

`verification_state: verified` means the source was readable, not that a contractor is approved or suitable. Missing fields can produce `uncertain`; source access failure produces `unverifiable`. A no-match is limited to the search and time shown.

## Pricing

Proposed launch price: **$0.02 per input lookup**, event `license-lookup`, with platform usage included. The Store pricing panel is authoritative once published. One lookup returning multiple name matches incurs one event, not one charge per row. A readable no-match is billable; a partial record marked `uncertain` can also be billable. A source failure marked `unverifiable` is not charged by this event.

At this price, 100 billable queries cost $2.00. Use a maximum charge of $2 for a full batch or $0.02 for one query. These are user settings, not a hard-coded dollar cap. No additional startup or automatic dataset-item fee is proposed. Check the displayed event settings before running.

## Limitations and legal notes

Only Louisiana is covered. Source records may be stale, incomplete or unavailable, and a name match may refer to another business. Verify directly with the [official board source](https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByNumber) before an important decision. This is not a certified license report, insurance check, eligibility decision or legal advice, and is not affiliated with the board.

Requests are rate-limited; login/CAPTCHA or access restrictions must not be bypassed. Automated access permission must remain valid. Do not use this Actor to evade source terms or collect unrelated personal information. No state-wide completeness or uptime guarantee is made.

For a technical problem, use this Actor's Apify Issues tab and share the input and run ID without credentials or private customer data.
