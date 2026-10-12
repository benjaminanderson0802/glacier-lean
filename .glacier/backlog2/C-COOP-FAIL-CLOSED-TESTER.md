# C-COOP-FAIL-CLOSED-TESTER — Verify claim drafts stay unfileable with missing proof

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `coop-release-evaluator`. Allowed edits: new `ventures/coop-postcards/tests/acceptance/test_C_coop_release.py` and `evidence/backlog2/C-COOP-FAIL-CLOSED-TESTER/`. Existing disputed checks, claim code, mail output and flows are read-only.

## Goal

Independently verify that complete local Markdown/PDF/JSON claim drafts retain the job and source links while `filing_ready` remains false if ad proof, payment evidence or current program terms are missing. This tests the safe reading of `DISPUTE.md`; do not certify a claim from incomplete evidence.

Read first: `ventures/coop-postcards/DISPUTE.md`, `ACCEPTANCE.md`, `PROOF.md`, `ventures/SPEC.md` co-op and mail rules.

## Drift check

- Checkpoint: PH12.13. PH5/PH9 remain in progress; PH12 work is owner-authorized.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: current shared rules, renderer and local fixtures; no mailing service or new block.
- Acceptance first: missing evidence produces a complete review draft plus explicit gaps, never a filing-ready verdict or external write.

## Verification

Run the new independent test and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/coop-postcards/tests`. Do not rewrite the disputed existing check or send/order mail.
