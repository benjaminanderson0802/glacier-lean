# PH9.1 first live weekly maintenance run

## Direction and acceptance

- Checkpoint: PH9.1, first live weekly run. No checkpoint status was changed.
- Dependencies: PH3 and PH7 have recorded exits; PH5 is still in progress. This is evidence for the in-progress PH9.1 item, not a PH9 exit.
- Properties and metrics: P-LOOPS (a recurring flow can run through Glacier), P-VERIFY (the saved proposal is independently checked), and M-SURVIVE (maintenance automation health).
- Existing tools: the repository already has its weekly flow, package index clients, scanner, and test commands. No new tool was added.
- Acceptance: install and start the flow through the authenticated Glacier API; finish all steps; save a proposal containing the actual run ID; pass the saved-note acceptance check; leave the fresh origin/main clone with empty `git status --porcelain`.

## Commands and environment

The initial clone was current `origin/main` at `fa866a3da7fdf0439dc2ee469e0b2be57d80ef35`. It was outside the worktree at `/tmp/glacier-w44-maint-live-origin-main`.

```sh
git clone --branch main --single-branch https://github.com/benjaminanderson0802/glacier-lean /tmp/glacier-w44-maint-live-origin-main
git -C /tmp/glacier-w44-maint-live-origin-main rev-parse HEAD
git -C /tmp/glacier-w44-maint-live-origin-main status --porcelain
cd /tmp/glacier-w44-maint-live-origin-main/glacier/web && npm ci
GLACIER_HOME=/tmp/glacier-w44-maint-live-home /home/glacier/w/workers/W44-maint-live/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 18765
```

`npm ci` completed successfully and installed 198 packages. The clone initially had no Python virtual environment, so the installed worktree interpreter was used to run the backend and test commands. The documented `/workspaces/glacier-lean/.venv/bin/python` path does not exist on this laptop. One initial backend start using that path returned “No such file or directory”; the command above started the backend successfully with a temporary `GLACIER_HOME`.

The flow was prepared from `flows/self/maintenance.json`, with `{repo}` paths set to the fresh clone and each bare `python` command set to the worktree interpreter. The maintenance command pointed to the clone’s `setup/selfbuild/maintenance.py`. It was installed with authenticated `PUT /api/environments/self-maintenance`, started with `POST /api/environments/self-maintenance/run`, and observed using `GET /api/runs/{run_id}`. These were HTTP API calls made with `httpx`; no maintenance Python function was called directly to start a run.

## Attempts

### API start rejected before a run was created

The first `POST /api/environments/self-maintenance/run` returned HTTP 400 with:

```text
This goal has no check yet. Add a way to check it is done before running it.
```

There was no run ID and no node ran. The maintenance flow declared a goal but had no acceptance check. I added a regression test and an acceptance command that verifies the saved proposal. The exact request time for this rejected start was not captured separately.

### Run `cb9f15003c75` — failed acceptance

The flow then ran from `2026-10-08T00:31:43Z` to `2026-10-08T00:52:59Z`. The API reported all five flow nodes `done`, but the run finished `failed` because the acceptance command used local `date.today()` (Oct 7 in Chicago) while the note step writes under the current UTC date (Oct 8). The command looked for the wrong file. The maintenance command also received the literal `{run}` and saved that literal instead of its run ID. The scanner wrote `tools/scan/proposals-2026-10-07.md` into the clone, so its `git status --porcelain` was not empty.

Observed node transitions (UTC):

| Time | Run state | Node states at observation |
|---|---|---|
| 00:31:43.247 | running | all pending |
| 00:31:45.300 | running | weekly done; health running; others pending |
| 00:42:05.839 | running | weekly, health done; scan running |
| 00:42:13.860 | running | weekly, health, scan done; maintenance running |
| 00:52:59.117 | failed | weekly, health, scan, maintenance, status_note done |

The acceptance error was `FileNotFoundError` for `/tmp/glacier-w44-maint-live-home/vault/proposals/maintenance-2026-10-07.md`; the saved note was at `proposals/maintenance-2026-10-08.md`. I removed the single untracked scanner output produced by this failed attempt before the final run and confirmed the clone was clean again.

I added tests first, observed them fail, then fixed command `{run}` expansion, redirected scanner output under `$GLACIER_HOME/tool-scan`, made acceptance use UTC, and made the maintenance command’s date UTC. The run ID expansion and redirected scanner output were confirmed in the final run.

### Run `6e7e71c9f56e` — completed

The final API start returned HTTP 200 at `2026-10-08T00:54:50.287Z`. The run reached terminal state `done` at `2026-10-08T01:15:44.585Z`; its saved-note acceptance check passed. Every node state and first observed transition time (UTC):

| Step | State | First observed at |
|---|---|---|
| weekly | done | 00:54:52.334 |
| health | done | 01:05:13.064 |
| scan | done | 01:05:21.079 |
| maintenance | done | 01:15:44.585 |
| status_note | done | 01:15:44.585 |
| saved-note acceptance | passed | 01:15:44.585 |

The `health` step reported: backend 458 passed, 1 skipped, 1 warning; other suites 68 passed; verification benchmark false-done rate 0.00% and verified rate 100.00%; security suite passed. The maintenance step reported backend tests 458 passed, 0 failed, 0 errors. Its screen check could not complete; see the environment limitation below.

The saved note is at `proposals/maintenance-2026-10-08.md` in the temporary Glacier vault. Its heading shows `2026-10-07`, because the fresh origin/main clone’s maintenance script uses the laptop’s local date; the vault note path uses Glacier’s UTC date. The note includes the actual run ID. The clone’s `git status --porcelain` was empty after the run and after the screen-check diagnostic.

The flow is proposal-only: nothing was installed into the clone or adopted. The npm dependency install was for test prerequisites and is ignored by Git. Scanner output went to the temporary Glacier home.

## Saved proposal note (full text)

```markdown
Weekly maintenance results. This is a proposal for the owner to review. Nothing was installed or changed.

# Weekly maintenance proposal — 2026-10-07

Run: 6e7e71c9f56e

This note suggests changes for the owner to review. Nothing was installed or changed.

## Safe to update

- mcp: 1.30.0 → 2.3.0 (python) — MIT licence; needs care because this changes the major version
- @ag-ui/client: 0.0.59 → 1.0.2 (npm:web) — MIT licence; needs care because this changes the major version
- @types/node: 24.19.1 → 26.6.4 (npm:web) — MIT licence; needs care because this changes the major version
- playwright: 1.63.0 → 1.64.0 (npm:web) — Apache-2.0 licence; no major-version jump
- typescript: 6.0.3 → 7.0.2 (npm:web) — Apache-2.0 licence; needs care because this changes the major version
- ws: 8.18.3 → 8.22.0 (npm:web) — MIT licence; no major-version jump

## Not proposed: licence

- agent-framework-core (python): 1.19.0 → 1.20.0; licence could not be confirmed as OSI open source (Location: /home/glacier/w/workers/W44-maint-live/.venv/lib/python3.12/site-packages).
- fastapi (python): 0.141.1 → 0.142.4; licence could not be confirmed as OSI open source (Location: /home/glacier/w/workers/W44-maint-live/.venv/lib/python3.12/site-packages).
- websockets (python): 16.1.1 → 17.2; licence could not be confirmed as OSI open source (Location: /home/glacier/w/workers/W44-maint-live/.venv/lib/python3.12/site-packages).
- jsonschema (python): 4.25.1 → 4.26.0; licence could not be confirmed as OSI open source (Location: /home/glacier/w/workers/W44-maint-live/.venv/lib/python3.12/site-packages).
- keyring (python): 25.6.0 → 25.7.0; licence could not be confirmed as OSI open source (Location: /home/glacier/w/workers/W44-maint-live/.venv/lib/python3.12/site-packages).

## Test board

- Backend tests: passed — 458 passed, 0 failed, 0 errors
  - Slowest tests: call     tests/test_vault_concurrency.py::test_concurrent_vault_api_reads_and_writes (24.13s); call     tests/test_core.py::test_schedule_creates_runs (12.26s); call     tests/test_runner_wiring.py::test_run_waits_at_effective_limit (11.26s); setup    tests/test_local_guard.py::test_hostile_websocket_origin_is_rejected (10.46s); call     tests/test_core.py::test_crash_mid_run_resumes_without_rerunning_finished_nodes (8.34s)
- Screen check: failed — could not check right now

## New tools worth a look

- No new tools met the open-source and activity checks.

Nothing was installed. To try one, approve it and a feature run will add it with tests.


Step results: health: done, maintenance: done, scan: done, status_note: running, weekly: done
```

## Screen-check environment limitation

The flow’s screen check was recorded as unavailable. I ran `npm run check:ui` once to identify the cause: theme lint, TypeScript, and the Vite build passed, then Playwright could not start Chromium because the laptop lacks the system library `libnspr4.so` (`error while loading shared libraries: libnspr4.so: cannot open shared object file`). Per the card instruction, I recorded the missing system dependency and did not retry or install OS packages.

## Regression checks and full backend suite

The focused regression checks passed:

```text
4 passed in 2.38s
```

The full backend suite was run after fetching and rebasing on `origin/main`, under the shared lock:

```sh
flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && ../../.venv/bin/python -m pytest -q tests'
```

Exact final line:

```text
495 passed, 1 skipped, 1 warning in 604.37s (0:10:04)
```

## Changes made for this live run

- Added the maintenance flow’s saved-note acceptance check.
- Expanded `{run}` in command steps so the maintenance proposal records its actual run ID.
- Directed tool-scan output into `GLACIER_HOME` so the clone remains unchanged.
- Used UTC consistently for the saved-note check and the maintenance proposal date.
- Corrected `docs/SELF_BUILD.md` to distinguish the feature-card launcher from starting the weekly environment through the API.

The temporary backend was stopped after the final note was retrieved. No process was pushed, published, or merged.
