# Verification proof — V-COOP2

Status: **fixture-tested and locally runtime-tested; live account behavior remains unverified**. PH12.13 is still in progress. This card does not mark a roadmap checkpoint done.

## Drift check

- Checkpoint: PH12.13, Co-op claims + street postcards.
- Dependencies: PH5 and PH9 remain in progress; the venture card is explicitly authorized to start before their exit, and this work does not mark the checkpoint done.
- Property and metric: P-CONTROL (owner-only filing and mailing), P-VERIFY (evidence-gated readiness), and M-VERIFIED.
- Existing tool: the shared read-only Jobber connector, rules checker, and deadline tracker cover connector/rules/deadline needs; the venture-specific adapter is glue for its claim-draft format and private-data filter (I-01).
- Acceptance: `ventures/coop-postcards/tests/acceptance/test_v_coop2.py`; no acceptance files were changed. The five-brand source/uncertainty check passes. The compact intake check creates artifacts but disputes its `filing_ready is True` assertion because the record omits required evidence and confirmed program terms; see `DISPUTE.md`.

## Acceptance and fixture evidence

Acceptance: a completed synthetic Jobber job produces local claim draft JSON, Markdown, and PDF with a source-linked brand record, evidence checklist, and deadline reminders; an active job is skipped; claim submission and mailing do not occur.

```sh
~/w/glacier-lean/.venv/bin/python -m pytest ventures/coop-postcards -q
```

Result: **11 passed, 1 xfailed, 1 xpassed**. The independent fixture acceptance test verifies local-only execution, the completed/active job distinction, the five-item checklist, Carrier source and unverified status, reminder dates, Markdown/PDF outputs, and that the legacy filing command takes no external action. The xpass is the now-satisfied five-brand check; the remaining expected failure is the disputed readiness assertion described below.

Independent V-COOP2 check with xfails ignored: `~/w/glacier-lean/.venv/bin/python -m pytest ventures/coop-postcards/tests/acceptance -q --runxfail` → **2 passed, 1 failed**. Passing checks cover all five source-linked brand records and safe route validation. The remaining failure is the disputed readiness assertion above; no owner-only action was performed.

The synthetic output is checked in at `evidence/fixture-output/`: a completed Carrier job with confirmed fixture expiry `2026-12-31` produced reminders on `2026-11-01` and `2026-12-01`. Its draft remains `filing_ready: false`; the supplied date is fixture data, not a verified Carrier deadline. The fixture also includes an active job that was ignored. Source fixture: `fixtures/jobber_completed_job.json`.

## Real local runtime

The checked-in claim flow was installed in a disposable Glacier backend and run using the synthetic fixture. All four nodes completed: `daily`, `create_drafts`, `claim_review`, and `record_review_only`. The local review approval records review only. Evidence is `evidence/live-run.json` and the same fixture draft artifacts above. No Jobber API call, brand portal, Lob request, mail order, payment, or filing occurred.

Postcard proof rendering remains local/test-only. The shared renderer outputs a 6x4 PDF; it has not been validated as a USPS EDDM flat print master. No postcard was published or mailed.

## Brand records and live limits

`brand-rules.json` has source-linked records for Carrier, Trane, Lennox, Rheem, and Goodman. Every record is marked `unverified`; where public program-specific terms are not available, the record says so and directs the owner to confirm current eligibility, terms, evidence, and deadline with the brand. Goodman’s linked APlus guide is explicitly historical. The source links do not prove a particular dealer’s enrollment or available funds.

No live Jobber account was connected or queried. Jobber read access uses the shared `JobberClient` also used by warranty and only requests job completion metadata, not client/homeowner fields. The owner still must create/configure the read-only Jobber app, confirm current brand rules and dates, authorize/sign/file claims directly, and approve each exact postcard proof and campaign. No account creation, signature, payment, filing, publication, or mailing was automated.

## Other venture test sweep

Existing individual venture suites were run with the project interpreter; the venture suites recorded in the task run passed. Two unrelated existing suite issues remain outside this card: `ventures/blocks/filer` cannot import Playwright in this worktree (`MODULE_NOT_FOUND`), and `ventures/recall-checker` has an existing expected-text mismatch (`no match in` vs `no match found in`). A combined `pytest ventures -q` also has existing collection import-path failures in Recall Actor and Utility Audits. No tests or checkers for those areas were changed.

The screen/runtime wrapper `npm run live` could not start its Vite screen because `glacier/web/node_modules/vite/bin/vite.js` is absent in this worktree. The backend runtime was started directly and the fixture flow was verified through its API. These environment gaps do not establish live account behavior.
