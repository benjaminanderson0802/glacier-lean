# Progress — Co-op claims and street postcards

PH12.13 remains **in progress**. The co-op flow now reads completed jobs through the shared read-only Jobber client, creates local claim drafts in Markdown and PDF, carries source-linked brand records and an evidence checklist, and schedules 60/30-day reminders only when an owner-confirmed program expiry is supplied. Claim filing is a manual dealer action; the approval node records review only. Postcard proofs remain local render-only output with no mail request.

Fixture and real-runtime proof are recorded in `evidence/`: one completed synthetic Carrier job produced a draft, the active fixture job was skipped, and the installed Glacier flow completed all four nodes after a local review approval. The generated draft is explicitly not filing-ready because the brand terms are unverified and evidence is incomplete. The co-op test suite passes; see `PROOF.md` for exact commands, results, and limits.

No live Jobber account, dealer record, brand portal, Lob API, mailing, payment, or filing was used. All five brand records are unverified for account-specific rules. The postcard proof PDF remains 6x4 and has not been verified as a USPS EDDM flat print master. PH5 and PH9 are still in progress, so this venture checkpoint is not marked done.
