# C-WARRANTY-RULES-TESTER — Independently check brand-specific warranty decisions

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `warranty-rules-evaluator`. Allowed edits: new `ventures/warranty/tests/acceptance/test_C_warranty_rules.py` and `evidence/backlog2/C-WARRANTY-RULES-TESTER/`. No brand rule tables, Jobber mapping, portal automation or existing checks.

## Goal

Freeze source-grounded cases for supported brands, registration deadlines, regional exceptions and unreadable model/serial inputs. Confirm the tool distinguishes brand policy from eligibility claims and returns uncertainty when the official source does not support a conclusion.

Read first: `ventures/warranty/ACCEPTANCE.md`, `PROOF.md`, `JOBBER-SETUP.md`, `brands/`, `ventures/SPEC.md`.

## Drift check

- Checkpoint: PH12.11. PH5/PH9 remain in progress; PH12 is owner-authorized.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: current rule tables, reader, pytest and official brand pages already linked by the venture; no new portal or dependency.
- Acceptance first: each frozen case matches its cited current source and exact product inputs; uncertain cases never generate a registration-ready result.

## Verification

Run the new independent checks and `~/w/glacier-lean/.venv/bin/python -m pytest -q ventures/warranty/tests`. No portal login, registration submission, homeowner email or live customer record.
