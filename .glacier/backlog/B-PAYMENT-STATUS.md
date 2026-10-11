# B-PAYMENT-STATUS — Stop treating a checkout return URL as payment evidence

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-PAYMENT-STATUS`; never push.

## Scope

Allowed edits: `ventures/blocks/customer/__init__.py`. Also allowed: `evidence/backlog/B-PAYMENT-STATUS/` and a card-specific claim in `vault/claims/`. New ordinary unit tests must live under the affected module’s `tests/unit/` and use this card ID in the filename; no existing test edits. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **customer**. Exclusive customer lane after B-SIGNATURE-AUTH; preserve protected recorded-response tests.

## Goal and evidence

/customer/success returns “Payment complete” on any matching URL without checking a payment record. This is an observed display path, not proof that billing state is corrupted.

Show a pending-verification result until recorded test-mode provider evidence confirms the exact checkout/customer. Keep canceled, pending and confirmed results distinct and make direct URL visits harmless.

Read first:

- [ventures/blocks/customer/__init__.py](../../ventures/blocks/customer/__init__.py) (create_signature_server, checkout_link)
- [ventures/blocks/customer/live_stripe_check.py](../../ventures/blocks/customer/live_stripe_check.py)

## Drift check

- Checkpoint: **PH12.6**. Properties: **P-VERIFY, P-CONTROL**. Metrics: **M-FALSE-DONE, M-AUDIT**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing Stripe test adapter and local records; no new payment vendor, live billing or new credentials.
- Value/effort estimate: **4/5 value ÷ 2 effort units = 2.00**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Independent recorded-provider tests cover a direct success URL visit, an unpaid/expired session, wrong-customer session and confirmed test payment. Only the last may display completion; no live key or charge.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/blocks/customer/tests`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
