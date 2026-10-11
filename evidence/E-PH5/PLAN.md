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

## Additional reproduced runtime gap

The first live runtime run wrote the exact bytes but exhausted its two attempts at
supervisor review. `_review` received only the worker handover and task title; the
independent command ran only after review, and neither its definition nor its result
was supplied to the supervisor. `review-before.log` reproduces the missing input.
Run command checks first and provide their evidence and definitions to review; retain
both the reviewer gate and the command gate. The governor also receives saved check
and review evidence. One fresh live retry after those changes is recorded below.

The focused backend suite also reproduced a fixture using `/tmp` as a task workspace;
the verifier tried to copy the shared temp root before review and recursed into its
own check directory. Reject filesystem and temp roots as unsafe check workspaces with
an explicit failed-check result. This preserves the independent-check gate while
preventing a verifier self-copy loop.

## Final verification (2026-10-11)

- Focused backend team, audit, and execution regressions: 57 passed. Full backend
  suite: 833 passed, 1 skipped, 7 failed in 18m23s. The seven failures are outside
  this lane; see `backend-full-final.log` and claim
  `CLM-2026-10-11-E-PH5-FULL-BACKEND-BOARD`.
- Fresh isolated live backend (`live-runtime-v2-*`): plan saved and started, approval
  state had zero attempts and no output file, then owner approval was recorded. The
  Codex worker created the exact 21-byte result and the independent command passed.
  The independent supervisor selected `granite3.3:2b` and failed twice; the team
  stopped at `needs_owner`. No further retries were made. See
  `live-runtime-v2-final.json` and claim `CLM-2026-10-11-E-PH5-LIVE-REVIEW`.
- Live interview requests returned HTTP 200. Live spec drafting returned HTTP 502
  twice, including after the EARS schema/prompt change; see the existing live-draft
  claim. The edited-goal/spec loss in the Build screen is also recorded separately
  because resolving it requires the parallel UI/API lane. Therefore the complete
  interview → edited spec → approved runnable plan path is not claimed as live-verified.
- Web checks ran in a copied directory layout with pinned dependencies from the
  existing lockfile, keeping the shared `node_modules` untouched. `npx tsc -b`,
  theme lint, i18n parity, and `npm run build` all passed. No screen files changed,
  so no screen-specific e2e spec was run.
