# CPSC data prep progress

Card V-CPSC2 advances PH12.9. PH12 depends on PH5 and PH9, whose phase exits
are recorded as reached; wave 6 assigns the venture in parallel. It serves
P-CONTROL and P-USABLE, with M-VERIFIED and M-INTERVENE, by keeping customer
review, certification, and filing under human control.

Implemented and fixture-tested: batch preparation, source-linked field and
gap review, customer certification gate, current-template CSV generation,
per-importer status board, test-mode checkout adapter, daily source refresh,
code-page previews with a publication approval, and broker launch approvals
that wait for the trade-lawyer opinion and owner's contract approval. Current
tests verify source IDs and intake-to-ruleset field mapping. These fixture
checks do not prove a real customer batch.

Live feeds checked on 2026-10-10: 589 CPSC HTS rows, 130 CPSC citation and
testing-exception rows, one Product Registry template record, and 10,047
CPSC Recalls API rows. Each source had no canary alerts, and an immediate
repeat sync reported `changed: false`. Results are recorded in
[`evidence/live-feed-canaries-2026-10-10.json`](evidence/live-feed-canaries-2026-10-10.json)
and summarized in [PROOF.md](PROOF.md). The earlier CPSC 403 report is stale
for these sources.

Paid launch on either channel and broker onboarding are still gated on the
owner's written trade-lawyer opinion about the exact flat-fee broker model
and direct batch plans. Use
[LAWYER-QUESTIONS.md](LAWYER-QUESTIONS.md) with counsel. No real-Glacier
end-to-end batch, customer certificate, live independent second-engine
extraction, customer certification, or CPSC submission was performed in this
card. Without configured `GLACIER_OLLAMA_URL` and `GLACIER_LOCAL_MODEL`, the
independent extraction remains uncertain and a batch cannot be released.
The owner continues to sign contracts, create accounts, pay, certify, file,
and approve any publication; Glacier does not automate those actions.

No PH12 checkpoint status was changed. Do not describe PH12.9 or this venture
as released until its real-data/sandbox acceptance and legal gate are
independently verified.

On 2026-10-10, the independent check
`test_lawyer_questions_are_cited_and_launch_remains_gated` passed with
`--runxfail` (1 passed). The complete venture suite passed with 19 passed, 1
skipped, and 1 xpassed. The lawyer opinion remains an owner step and launch
gate; these test results do not constitute counsel's opinion.
