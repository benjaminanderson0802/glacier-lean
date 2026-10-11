# PH9.1 maintenance board verification

## Drift check

1. Checkpoint: PH9.1, independent verification of the maintenance Environment. PH3 and PH7 exits are owner-approved; PH5 remains in progress, so this is evidence only and does not close PH9.
2. Dependencies: PH3 and PH7 have recorded exits; PH5 is still in progress as stated by the card.
3. Properties and metrics: P-VERIFY and P-CONTROL; M-VERIFIED and M-AUDIT.
4. Existing tools: reuse pytest's isolated-home/free-port fixtures, the existing authenticated backend API, and the maintenance flow. No duplicate runner or dependency is being added.
5. Acceptance, written before execution: on a disposable clone with a unique GLACIER_HOME, isolated Python/npm dependency directories, and a unique loopback port, complete the maintenance Environment, confirm its proposal note and acceptance check, and confirm `git status --porcelain` in the clone is empty. Do not use `/tmp/e2edata`, shared dependencies, fixed port 8000, or execute either legacy launcher.

## Legacy launcher review

Inspect source only. Record why `setup/run_core_tests.sh` and `setup/live_codex_check.sh` are unsafe without executing them or reproducing their destructive behavior.
