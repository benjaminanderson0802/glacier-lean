# B-OFFLINE-PROOF — Prove the offline pack works without network access

Owner: Benjamin. Proposed launch card from T-FIND, 2026-10-10. Read [INDEX.md](INDEX.md#launch-contract), AGENTS.md, NORTHSTAR.yaml and ORCHESTRATION.yaml first. Commit on `card/B-OFFLINE-PROOF`; never push.

## Scope

Allowed edits: `new evidence/backlog/B-OFFLINE-PROOF/ artifacts only`. Also allowed: `evidence/backlog/B-OFFLINE-PROOF/` and a card-specific claim in `vault/claims/`. Tester-only: the scope above is the full check/data authorization. Existing tests, acceptance files and CHECK.md files are read-only. No other paths are authorized.

Exclusive lane: **offline-evaluator**. Test only PH10 offline pack, not E-PH8’s desktop installer/auto-update. Linux evidence cannot stand in for owner Windows proof; no release/upload.

## Goal and evidence

The offline-pack tests mock wheel downloads, environment creation and install commands; those passes alone do not prove a complete network-disabled install.

Independent verification assignment: build the existing Linux pack using current pins, install in a disposable local destination with network disabled, and run a deterministic automation using the shipped source/docs. Use an already available local model only if claiming model proof.

Read first:

- [setup/offline/test_offline.py](../../setup/offline/test_offline.py)
- [setup/offline/build_pack.py](../../setup/offline/build_pack.py)
- [setup/offline/install_pack.py](../../setup/offline/install_pack.py)
- [NORTHSTAR.yaml](../../NORTHSTAR.yaml) (PH10.3)

## Drift check

- Checkpoint: **PH10.3**. Properties: **P-PORTABLE, P-USABLE**. Metrics: **M-LOCAL, M-VERIFIED**.
- Dependencies: use the phase ledger in INDEX; assignment permits scoped work, not a phase-exit claim. Recheck dependencies at dispatch; no NORTHSTAR status edits here.
- Existing-tool choice (I-01): Existing offline builder/installer and OS isolation; no new installer or release pipeline.
- Value/effort estimate: **4/5 value ÷ 3 effort units = 1.33**. Estimates prioritize impact and unblocking, not promised revenue.

## Verification — specified before implementation

Capture commands, pack hash, installed versions and a real output with network blocked. Missing wheels/tools are explicit failures and claims; do not edit pack code or its checks to make the proof pass.

Run `~/w/glacier-lean/.venv/bin/python -m pytest -q setup/offline/test_offline.py`. Builders first reproduce the defect and have an independent evaluator freeze any missing acceptance case; ordinary unit tests do not substitute for that evaluator. Tester-only cards never repair the product they judge. Follow the launch contract for real-backend proof and final reporting.

Finish with commit hash, changed files, commands/results, fixture versus real evidence, and remaining owner steps. Do not send, publish, sign, file, spend, create accounts, delete owner data or decide legal questions. Use synthetic/local evidence unless an already-authorized read-only source is available.
