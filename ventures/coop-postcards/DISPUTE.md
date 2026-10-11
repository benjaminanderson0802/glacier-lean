# Acceptance dispute — V-COOP2

## `test_fixture_jobber_intake_creates_claim_draft_artifacts`

The adapter creates local Markdown, PDF, and JSON artifacts from this compact
Jobber-shaped record, includes its Carrier source link and evidence checklist,
and returns a reminder to confirm the applicable deadline. The check still fails
at `assert result["filing_ready"] is True`.

That assertion conflicts with acceptance item 3 and the venture's filing guard:
the supplied record has no ad proof, no proof of payment, and no confirmed program
expiry. Carrier's source-linked record is explicitly `unverified`; it does not
establish current eligibility, evidence requirements, or a deadline. Treating
this draft as filing-ready would certify missing and uncertain evidence.

A corrected check should assert that the adapter creates `.md`, `.pdf`, and `.json`
artifacts, retains job `9001` and the unverified Carrier source, returns a deadline
confirmation reminder, and has `filing_ready is False` with the missing evidence
and unverified program terms called out. Once the owner supplies the missing
evidence documents and confirms current terms and expiry, a separate readiness
check can evaluate that completed packet.
