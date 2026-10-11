# C-CLOSEOUT-PILOT-TESTER — Independently verify the five-packet closeout promise

Owner: Benjamin. Role: **TESTER only**. Proposed for the 2026-10-11 round-2 backlog.

## Scope

Exclusive lane: `closeout-pilot-evaluator`. Allowed edits: new `ventures/job-closeout/tests/acceptance/test_C_closeout_pilot.py`, `evidence/backlog2/C-CLOSEOUT-PILOT-TESTER/`, and a card-specific claim. Do not edit generator code, existing checks, sales copy, or customer data.

## Goal

Independently check that a five-packet sample retains source values, marks missing or malformed source fields uncertain, and produces a reviewable packet without claiming compliance or sending anything. This supports the $49 closeout offer ranked first in FASTEST-MONEY; it does not establish buyer demand or authorize outreach.

Read first: `ventures/job-closeout/ACCEPTANCE.md`, `PILOT.md`, `TEST-FINDINGS.md`, `PROOF.md`, `ventures/SPEC.md`.

## Drift check

- Checkpoint: PH12.8 / PH12.22 integration evidence. PH5 and PH9 remain in progress; PH12 work is explicitly owner-authorized in parallel.
- Properties/metrics: P-VERIFY, P-USABLE; M-VERIFIED, M-INTERVENE.
- Existing tools: use the current generator, pytest and synthetic fixtures; no new dependency.
- Acceptance first: frozen source-to-output cases for five accurate packets plus missing, malformed-date and partial-source cases; all uncertainty is visible and no delivery side effect occurs.

## Verification

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/job-closeout/tests/acceptance/test_C_closeout_pilot.py` and the unchanged `ventures/job-closeout/tests` suite. Record fixture-through-engine evidence separately from customer evidence. Preserve every existing test ID and behavior.
