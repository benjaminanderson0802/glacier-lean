# C-FREIGHT-INTAKE-TESTER — Independently verify source-linked freight claim intake

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `freight-intake-evaluator`. Allowed edits: new acceptance check under `ventures/freight-claims/tests/acceptance/` named with `C-FREIGHT-INTAKE` and `evidence/backlog2/C-FREIGHT-INTAKE-TESTER/`. No parser, claim builder, mail, filer or existing checks.

## Goal

Freeze source-to-packet cases for shipment IDs, delivery dates, damage evidence, carrier rules and claim deadlines. Ensure partial or unsupported source rows remain uncertain and no generated packet claims a recovery or authorizes filing.

Read first: `ventures/freight-claims/ACCEPTANCE.md`, `PROOF.md`, `incoming/CUSTOMER-INTAKE.md`, `ventures/SPEC.md` freight section.

## Drift check

- Checkpoint: PH12.14. PH5/PH9 remain in progress; PH12 work is owner-authorized.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: existing CSV intake, source templates and pytest; no carrier integration.
- Acceptance first: every packet fact maps to an input row/source, incomplete records are marked uncertain, and no carrier submission or customer mail occurs.

## Verification

Run the new check and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/freight-claims/tests`. Use synthetic data and label engine output as fixture-through-engine proof, not carrier/customer evidence.
