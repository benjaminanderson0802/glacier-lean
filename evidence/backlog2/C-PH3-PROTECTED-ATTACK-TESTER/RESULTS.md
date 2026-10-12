# C-PH3-PROTECTED-ATTACK-TESTER

## Drift check

- Checkpoint: PH3.2; its independent attack evidence is explicitly pending. PH3 has owner exit approval; PH3.2 remains in progress. PH2 has not exited, but this assigned independent tester card is parallel-safe under the phase's explicit approval.
- Properties and metrics: P-VERIFY and P-SECURE; M-VERIFIED and M-SECURITY.
- Existing tools: pytest, stdlib path inspection, and the workflow's pre-work protected-file snapshot. No new security framework was added.
- Acceptance: reject symlink, wrong-type, deletion, creation, replacement, and portable traversal attacks with failed-verification evidence; no redirected outside target changes; allow a saved verifier-only file to be absent from the worker workspace when its baseline was absent.

## Evidence

- `cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_C_protected_path_attacks.py` — 12 passed. Output: `targeted.log`.
- `cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_verification.py` — 11 passed. Output: `verification-regression.log`.
- The literal `/workspaces/glacier-lean/.venv/bin/python` documented in the repo instructions is not present in this checkout. Used the same project venv via `/home/glacier/w/glacier-lean/.venv/bin/python`.

The new checks exercise API runs against a real local backend. Symlink attacks assert that an outside sentinel remains unchanged; the dangling-link attack also asserts that the redirected target stays absent. Failed runs assert `status=failed`, `verified=false`, a failed verification record, and attack-specific evidence ending in `not accepted`. The verifier-only file case passes and confirms the check file remains absent from the worker workspace.
