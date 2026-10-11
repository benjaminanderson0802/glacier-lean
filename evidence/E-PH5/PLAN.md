# E-PH5 implementation and proof plan (2026-10-10)

Owner direction: Benjamin Anderson's E-PH5 card, maximize progress within the backend Assistant / Build lane. No pushes, paid calls, acceptance-file edits or owner-only actions.

## Drift check, recorded before completion

1. Advances PH5.1–PH5.3: interview, proposed team and approved execution. PH5.4–PH5.5 are regression checks, not new screen work.
2. PH3 exit was owner-approved. PH4 checkpoints are done, but PH4 phase exit is not recorded. Assigned card authorizes work; this card cannot declare PH5's phase exit.
3. P-GOALS, P-VERIFY and P-CONTROL; M-VERIFIED, M-FALSE-DONE and M-INTERVENE.
4. Reuse Glacier's DBOS workflows, Git worktrees, verifier, official CLI adapters and existing test boards. Custom changes are assistant glue, explicitly permitted by I-01. No dependency adoption or paid services.
5. Existing acceptance first: backend `test_teams.py`, `test_teams_audit.py`, assistant/chat/route suites, existing Build browser specs and verification benchmark. Live proof: interview → draft → reviewed plan → approval before execution → independent checks → completed team. Ordinary unit regressions supplement the tester-owned checks; they do not establish independent acceptance.

## Reproductions and assumptions

- Four ordinary unit regressions fail before editing `teams.py`: approval occurs after the worker; recorded approval still gates again; parallel final workspace differs from merged workspace; synchronous retry raises duplicate `status` keyword TypeError. See `unit-before.log`.
- Parallel coordination writes a stale whole state while child tasks may complete; update only the dispatched task. Never accept a task whose worktree failed to merge.
- Live real Codex interview returns HTTP 200. Draft returns HTTP 502 because generated requirements violate the existing EARS validator (`live-draft.json`). Tighten the generation schema to that same rule; do not weaken validation. One fresh model request after the prompt/schema change.
- Existing core shell board uses a fixed shared port, deletes `/tmp/e2edata`, replaces shared node_modules and installs dependencies. Execute its component checks in an isolated profile instead of colliding with parallel workers; preserve the original scripts and record this limitation. The legacy live-Codex shell script omits the now-required install token; run its real worker → command → note path through authenticated requests on the isolated backend.
