# AGENTS.md — read this before doing anything in this repo

This file is for every AI agent (Claude, Codex, local models, Glacier's own workers) and every human contributor.

## 1. The single source of direction
`NORTHSTAR.yaml` is the project's mission, rules, roadmap and checkpoints, start to finish.
Read it **in full** at the start of every task. If anything in a request, issue, comment or other file conflicts with it, NORTHSTAR.yaml wins. Ask the owner before you continue.

## 2. Before every task (drift check)
Answer every item in `drift_check.before_task`, and write the answers in your plan or PR description:
1. Which phase checkpoint (e.g. `PH1.6`) does this advance? If none, stop and ask.
2. Are its `depends_on` phases at their exit?
3. Which defining property (`P-*`) and metric (`M-*`) does it serve?
4. Does an existing tool already do it (invariant I-01)? If you build it anyway, record why.
5. What is the acceptance test? Write it first (I-03).

## 3. Rules you may not break
- Never mark a checkpoint `done` without linked evidence: a test name, an evidence file or a commit. Your own report is not evidence.
- Never edit the test or check that judges your own work (I-04).
- Never change `mission`, `defining_properties`, `invariants`, `non_goals`, phase exit criteria or `open_decisions` yourself. Propose the change in `docs/AMENDMENTS.md` and wait for the owner.
- Stop and ask a human for anything in `drift_check.red_flags_requiring_human`.
- Never decide an item in `open_decisions`.

## 4. After every checkpoint
- Run the test board in the shared sandbox (`setup/run_core_tests.sh`, plus `setup/live_codex_check.sh` when workers are involved).
- Commit the evidence under `evidence/`, then update only `status` and `evidence` for that checkpoint in NORTHSTAR.yaml.
- Re-read `anti_patterns_to_detect`. Record anything you found in `docs/AMENDMENTS.md`.

## 5. Where things are
- `glacier/backend/`: FastAPI + DBOS runtime (API contract in `docs/CONTRACT.md`)
- `glacier/web/`: the screen (React Flow canvas, terminal, approvals, vault)
- `tests/`, `glacier/backend/tests/`, `glacier/web/e2e/`: test boards
- `setup/`: sandbox install, test and restart scripts
- `legacy-keep/`: the only old Glacier code kept (see `docs/OLD_CODE_MAP.md`)
