# C-PH3-PROTECTED-ATTACK-TESTER — Independently attack protected-check handling

Owner: Benjamin. Role: **TESTER only**.

## Scope

Exclusive lane: `verification-protection-evaluator`. Allowed edits: new `glacier/backend/tests/test_C_protected_path_attacks.py` and `evidence/backlog2/C-PH3-PROTECTED-ATTACK-TESTER/`. Do not change `verify.py`, `runner.py`, existing checks or security rules.

## Goal

Turn the remaining PH3.2 gap into independent adversarial coverage for protected files: file/parent/dangling symlinks, non-regular files, deleted or newly created checks, portable path traversal, and verifier-only files absent before work. Assert no outside write and correct failed-verification evidence.

Read first: claim `2026-10-10-e-ph3-independent-protection.md`, `glacier/backend/verify.py`, `glacier/backend/runner.py`, existing `tests/test_verification.py`.

## Drift check

- Checkpoint: PH3.2. PH3 has explicit owner exit approval; PH3.2 remains `in_progress` and requires independent evidence.
- Properties/metrics: P-VERIFY, P-SECURE; M-VERIFIED, M-SECURITY.
- Existing tools: pytest, stdlib path inspection and existing protected-file snapshot; no new security framework.
- Acceptance first: every attack is rejected or safely ignored according to the documented baseline, no out-of-root target changes, and protected content cannot be silently replaced.

## Verification

Run the new tests and relevant backend verification tests with the project interpreter. Tests remain evaluator-owned and read-only to implementation workers; report any unclear contract as a claim, not an invented policy.
