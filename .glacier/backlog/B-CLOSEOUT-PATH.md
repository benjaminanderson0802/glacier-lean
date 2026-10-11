# B-CLOSEOUT-PATH — Keep closeout packets inside their output directory

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-CLOSEOUT-PATH`; never push.

## Scope

Allowed edits: `ventures/job-closeout/scripts/generate_packet.py`. Also allowed: `evidence/backlog/B-CLOSEOUT-PATH/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **closeout**. No active-card dependency; take the exclusive lane before editing.

## Goal and evidence

write_packet interpolates externally supplied job_number directly into both output paths. Containment and collision behavior are not checked there; reproduce before changing.

Use a stable path-safe identifier for artifact names, preserve the displayed job number, and prevent collisions and symlink escape without overwriting another job.

Read first:

- [ventures/job-closeout/scripts/generate_packet.py](../../ventures/job-closeout/scripts/generate_packet.py) (write_packet)

## Drift check

- Checkpoint: **PH12.8**. Properties: **P-SECURE, P-USABLE**. Metrics: **M-SECURITY, M-INTERVENE**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): pathlib and existing hashing utilities; small validation glue. No new file-storage service.
- Value/effort estimate: **5/5 value ÷ 1 effort units = 5.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent cases with separators, parent traversal, Unicode and duplicate display numbers stay inside a temporary output root, preserve display text, and keep distinct jobs distinct.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/job-closeout/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
