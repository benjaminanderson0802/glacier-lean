# B-TEMPLATE-BOUNDARY — Independently verify imported template provenance and approval boundaries

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-TEMPLATE-BOUNDARY`; never push.

## Scope

Allowed edits: `new tests/backlog/test_template_boundary.py; new evidence/backlog/B-TEMPLATE-BOUNDARY/ artifacts`. Also allowed: `evidence/backlog/B-TEMPLATE-BOUNDARY/` and a card-specific claim in `vault/claims/`. Tester-only: the scope above is the full check/data authorization. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **template-evaluator**. Independent evaluator owns new checks only; no product, existing tests, UI or E-PH3 enforcement edits. Route any discovered bug to the owning builder via claim.

## Goal and evidence

The roadmap cites manifest digest, reviewer and command-review behavior; remaining value is independent adversarial proof of the complete import boundary, outside the active core-builder scope.

Tester-only card: derive cases from the contract for digest tampering, replaced commands after review, traversal and unreviewed capabilities. Exercise existing public APIs on a disposable real backend and report results.

Read first:

- [NORTHSTAR.yaml](../../NORTHSTAR.yaml) (PH10.4)
- [templates/](../../templates/)
- [docs/CONTRACT.md](../../docs/CONTRACT.md)

## Drift check

- Checkpoint: **PH10.4**. Properties: **P-SECURE, P-CONTROL**. Metrics: **M-SECURITY, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing manifest, API and pytest tools; no new provenance framework.
- Value/effort estimate: **4/5 value ÷ 3 effort units = 1.33**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

An unchanged reviewed template imports normally; tampered or unapproved inputs never become executable authority and failures are visible. Retain exact API responses and audit references.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q templates`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
