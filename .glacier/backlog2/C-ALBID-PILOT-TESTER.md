# C-ALBID-PILOT-TESTER — Independently verify an Alabama bid-triage sample

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `al-bid-pilot-evaluator`. Allowed edits: new `ventures/al-bid-triage/tests/acceptance/test_C_al_bid_pilot.py`, `evidence/backlog2/C-ALBID-PILOT-TESTER/`, and a card-specific claim. Do not edit triage code, existing checks, prospect files or outreach material.

## Goal

Check that each sample notice carries its supplied issuer, deadline and official source, while missing facts or conflicting notice IDs become `uncertain — please check`. This advances the second FASTEST-MONEY pilot path without claiming that Alabama Builds is complete, that a prospect is interested, or that automated collection is permitted.

Read first: `ventures/al-bid-triage/ACCEPTANCE.md`, `TEST-FINDINGS.md`, `README.md`, `PILOT.md`, `ventures/SPEC.md`.

## Drift check

- Checkpoint: PH12.22 (pilot-kit integration) and PH12.5 feed evidence. PH5/PH9 remain in progress; PH12 parallel work is owner-authorized.
- Properties/metrics: P-VERIFY, P-USABLE; M-VERIFIED, M-INTERVENE.
- Existing tools: current parser, pytest and source-linked fixture records; no new service.
- Acceptance first: independently freeze source facts and expected outcomes before running the unchanged generator; exact duplicate conflicts must not disappear silently.

## Verification

Run the new check and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/al-bid-triage/tests`. Label fixtures and the one public read-only canary separately; do not fetch or scrape notices beyond the existing authorized canary.
