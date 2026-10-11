# C-CARPENTER-COMMISSION-TESTER — Independently verify the signed commission basis

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `carpenter-commission-evaluator`. Allowed edits: new independent acceptance cases under `ventures/carpenter-goods/tests/acceptance/` named with `C-CARPENTER-COMMISSION` and `evidence/backlog2/C-CARPENTER-COMMISSION-TESTER/`. No commission implementation, existing checks, agreement terms or merchant exports.

## Goal

Freeze cases for item subtotal after discounts, shipping/tax exclusion, partial/full refunds, multiple amount columns, mixed/unsupported currency and rounding. The result must follow the supplied signed terms or remain uncertain; no amount is payable from unsigned/incomplete terms.

Read first: `ventures/carpenter-goods/ACCEPTANCE.md`, `PROOF.md`, `agreement/commission-summary.md`, `agreement/commission-agreement.md`, `TEST-FINDINGS.md`.

## Drift check

- Checkpoint: PH12.20. PH5/PH9 remain in progress; PH12 work is owner-authorized. Signed partner terms remain an owner gate, not a tester assumption.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: current CSV readers, decimal arithmetic and pytest; no billing integration.
- Acceptance first: only an explicitly supplied signed basis yields a deterministic amount; unsupported currency, ambiguous columns or missing terms are uncertain and no payment is sent.

## Verification

Run the independent acceptance file and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/carpenter-goods/tests`. Use synthetic exports; never infer a signed agreement or contact/publish for the maker.
