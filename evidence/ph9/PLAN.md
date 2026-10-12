# E-PH9 verification plan (2026-10-10)

Owner direction: Benjamin Anderson approved E-PH9 and maximum progress, with verified merges only, no protected-branch auto-merges, no pushes, no paid services, and owner gates retained.

## Drift check

1. This card advances current verification of PH9.1 maintenance, PH9.2 feature flow, and PH9.3 discovery. All three are already marked done in NORTHSTAR; `docs/AUDIT_FINAL.md` lists current live coverage as partial. No implementation gap is assumed from the older audit wording.
2. PH3 has an approved exit; PH7 is done with an approved exit. PH5 remains in progress, although its checkpoints are done. Assignment authorizes starting; PH9 phase closure remains with the integrator after dependency/exit review.
3. P-VERIFY, P-CONTROL, P-GOALS; M-VERIFIED, M-FALSE-DONE, M-AUDIT, M-INTERVENE.
4. Reuse the existing Glacier Environments, git worktrees/merge queue, pytest, and scanner. No new tool or dependency is needed. Pinned web dependencies may be provisioned privately using the existing lockfile; shared dependencies must not be modified.
5. Acceptance is the existing tester-owned `test_selfbuild_flows.py`, `test_selfbuild_install_commands.py`, `test_maintenance_flow.py`, `test_workspaces.py`, and `test_merge_lock.py`, plus the unchanged live maintenance graph's saved-note gate and the existing project test board. A current real feature shipment additionally needs every saved feature check and the owner's final review. No existing test, ACCEPTANCE.md, guard, or flow acceptance definition will be edited.

## Execution

- Run the focused existing suites and the prescribed screen checks.
- Start a real backend on a free loopback port with a fresh home. Install the unchanged maintenance flow through its existing installer and run it against a disposable clone of this exact source commit. Capture the saved run, proposal, health report, and Git status.
- Fetch public discovery sources through the existing scanner and preserve candidate/proposal/failure metadata. No candidate is adopted.
- Retain historical three-feature evidence as historical; do not claim a new real feature based on fixture workers, a smoke test, or a self-report.
- Use only the card branch for evidence commits. Do not merge a protected branch, approve a human gate, push, or update protected roadmap rules.
