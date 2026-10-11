# C-FDA-READER-BOUNDARY-TESTER — Check that uncertain reader fields block FDA packets

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `fda-reader-evaluator`. Allowed edits: new `ventures/fda-cosmetics/tests/acceptance/test_C_reader_boundary.py` and `evidence/backlog2/C-FDA-READER-BOUNDARY-TESTER/`. FDA and reader implementation, existing checks and label fixtures are read-only.

## Goal

Use independent label examples to verify agreement and disagreement handling across the shared reader and FDA packet preparation. A disputed value may be retained for review, but uncertainty must prevent a release-ready listing archive. Report every field and source page.

Read first: `ventures/fda-cosmetics/DISPUTE.md`, `ACCEPTANCE.md`, `PROOF.md`, `ventures/blocks/reader/CHECK.md`, claim `2026-10-10-ph12-15-reader-conflict-contract.md`.

## Drift check

- Checkpoint: PH12.15 and PH12.4 shared reader. PH5/PH9 remain in progress; PH12 is owner-authorized.
- Properties/metrics: P-VERIFY, P-CONTROL; M-VERIFIED, M-AUDIT.
- Existing tools: shared reader/rules blocks and current FDA packet tests; no second parser.
- Acceptance first: known fields preserve page provenance; disagreement or missing page evidence remains uncertain and blocks final packet output.

## Verification

Run the new test, the existing reader suite and FDA suite separately. Do not alter the disputed shared-reader contract; if its expected value semantics remain unclear, file a claim before test conclusions.
