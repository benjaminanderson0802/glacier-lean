# C-TEMPLATE-APPROVAL-TESTER — Freeze independent template approval-swap coverage

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `template-approval-evaluator`. Allowed edits: new `tests/backlog/test_C_template_approval_snapshot.py` and `evidence/backlog2/C-TEMPLATE-APPROVAL-TESTER/`. Product code, existing tests and template bundles are read-only.

## Goal

Convert the independent finding in `CLM-2026-10-11-B-TEMPLATE-BOUNDARY-APPROVAL-SWAP` into a stable external check: after review, changed commands or added capabilities cannot be approved as the reviewed template. Include unchanged-template approval, encoded traversal, unknown step and side-effect cases.

Read first: the claim, `docs/TEMPLATES.md`, current template import API in `docs/CONTRACT.md`, `NORTHSTAR.yaml` PH10.4.

## Drift check

- Checkpoint: PH10.4. PH8/PH9 remain in progress; PH10 work is built but independent evidence is needed before relying on the checkpoint.
- Properties/metrics: P-VERIFY, P-CONTROL, P-SECURE; M-VERIFIED, M-AUDIT, M-SECURITY.
- Existing tools: current template API, immutable reviewed snapshot and pytest; no new review layer.
- Acceptance first: approval succeeds only for byte-equivalent reviewed command/capability content; a changed proposal remains pending and non-installable.

## Verification

Run the new independent API test against a disposable real backend and current mock. Do not change production templates or existing judging tests; send the frozen test to the assigned builder.
