# Glacier feature audit

Date: 2026-10-09

Original audit branch: `card/gf-A1`; B5 follow-up: `card/gf-B5`

The original audit below records what was observed before B5. Its follow-up evidence and corrected rows are recorded under E8–E12.

## Findings

- The original real-backend screen run could save flows, run them, stream node state, show run history and terminal output, and handle approval/rejection. B5 fixed the flow-history lookup and verified assistant apply → history → undo on a real temporary backend (E8); the backend integration regression also passes (E9).
- The original full backend suite ended **2 failed, 718 passed, 1 skipped**. The scheduler test now passes with a wider real-scheduler window (E9). The live-log test is still unresolved and has a filed claim; it remains PARTLY (E12).
- `npm run check:ui` passed all 21 steps, including 16 browser specs. These browser specs use the mock backend; only the separate live core run exercised the screen against the real API.
- The original `bench/ph10/run_ph10.py` failed the guide/help check. B5 registered and rendered Settings help; `check_docs.py`, guide labels, and a browser F1 navigation spec now pass (E10). The prior template, Spanish, flow import/export, A2A, MCP, ACP stand-in, AG-UI, and AGENTS.md results remain in E7.
- Earlier live OpenCode ACP runs failed, but a B5 live rerun passed through OpenCode and Codex ACP with both backend and independent checks (E11; updated `evidence/live/acp_two_harnesses.md`).

`WORKS` means this audit saw a current real-backend operation or a focused acceptance check pass. `PARTLY` means only isolated tests, a mock screen, historical evidence, or a limited smoke check passed, or the run was load-sensitive. `BROKEN` means a current, reproducible user-visible path failed. The backend test suite starts real server processes with isolated homes, but model/CLI integrations in those tests are often fakes.

## Evidence commands and output

### E1 — full backend suite

Command:

```sh
flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests'
```

Output:

```text
FAILED tests/test_core.py::test_schedule_creates_runs - assert 0 >= 2
FAILED tests/test_core.py::test_codex_streams_live_log_while_running - assert...
2 failed, 718 passed, 1 skipped, 5 warnings in 720.40s (0:12:00)
```

The failures were rerun without code or test changes:

```sh
flock /tmp/glacier-suite.lock bash -c 'cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_core.py::test_schedule_creates_runs tests/test_core.py::test_codex_streams_live_log_while_running'
```

```text
..                                                                       [100%]
2 passed in 18.92s
```

### E2 — UI board (mock backend)

Command: `cd glacier/web && npm run check:ui`

Output excerpt:

```text
theme lint ok (45 files)
i18n parity: 2 dictionaries, 766 keys; keys and placeholders match
[check-ui] step 21/21 window_controls.spec.mjs
[window-controls] ok   browser build has no window controls
[window-controls] ok   desktop build shows minimise and close controls
[window-controls] ok   minimise calls the Tauri window bridge
[window-controls] ok   close calls the Tauri window bridge
[check-ui] PASS
```

The run included `core`, build interview/team, delete/undo, every-control, home, HTTP step, layout, memory map, shell, Spanish, triggers, updates, W97/W98 and window-control specs. It generated screenshots under `evidence/ui/`; those generated changes were restored after the board.

### E3 — real backend + production screen, core flow

The disposable backend used `GLACIER_HOME=/tmp/glacier-a1-live`, `GLACIER_TOKEN=a1-audit-token`, `GLACIER_DEV=1`, and `CODEX_BIN=glacier/backend/tests/fake_codex.py`. `GLACIER_DEV=1` was needed because the local-request guard only permits browser dev origins on ports 4173/5173. No external model API or paid service was called.

Backend start command (from `glacier/backend`):

```sh
GLACIER_HOME=/tmp/glacier-a1-live GLACIER_TOKEN=a1-audit-token GLACIER_DEV=1 CODEX_BIN="$PWD/tests/fake_codex.py" ~/w/glacier-lean/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

Command (from `glacier/web`):

```sh
UI_PORT=4173 SKIP_MOCK=1 API_URL=http://127.0.0.1:8765 GLACIER_TOKEN=a1-audit-token GLACIER_HOME=/tmp/glacier-a1-live node e2e/core.spec.mjs
```

Behavior output:

```text
[e2e] ok   screen loaded, live events socket connected
[e2e] ok   new environment appears in list
[e2e] ok   saved, commit 7260c37d
[e2e] ok   nodes n1, n2 turned done via live events
[e2e] ok   run status shows done
[e2e] ok   run history lists the run as done
[e2e] ok   clicking n1 shows its output in the xterm terminal
[e2e] ok   approval prompt shown
[e2e] ok   approved: banner gone, n3 done, run done
[e2e] ok   rejected run: n3 skipped, status rejected
[e2e] ok   loop ran twice then exited (got "finished 2 of 2")
[e2e] ok   sub-flow node opens the child run with its node states
[e2e] ok   codex node done with prompt filled
[e2e] FAIL no page errors: Failed to load resource: the server responded with a status of 400 (Bad Request) @ http://localhost:4173/api/memory/history?path=environments%2Fe2e-flow.json
FAIL (1 failing checks)
```

The same 400 occurred for the other saved flow version-history requests (`approval-flow`, `codex-flow`, `sub-child`, `loop-flow`, and the auto-wire/decide flows). Flows still saved and ran. A separate live-screen save check returned `PASS real backend UI saved flow; name visible: true`, `page errors: []`; `GET /api/environments` then returned `[ {"id":"a1-live-audit","name":"A1 live audit"} ]`.

### E4 — authenticated live API inventory

Command (project interpreter; standard-library `urllib`; disposable install token):

```sh
~/w/glacier-lean/.venv/bin/python - <<'PY'
import json, urllib.request
base='http://127.0.0.1:8765'; token='a1-audit-token'
paths={'home':'/api/home','node-types':'/api/node-types','environments':'/api/environments','runs':'/api/runs','vault':'/api/vault/notes','memory notes':'/api/memory/notes','memory graph':'/api/memory/graph','memory hygiene':'/api/memory/hygiene','memory search':'/api/memory/search?q=a1&mode=keyword','memory compatibility':'/api/memory/compat','assistant settings':'/api/assistant/settings','assistant conversations':'/api/assistant/conversations','teams':'/api/teams','claims':'/api/claims','secrets':'/api/secrets','system check':'/api/system/check','system settings':'/api/system/settings','costs/usage':'/api/costs','templates':'/api/templates','starter':'/api/starter','imports':'/api/imports','sessions':'/api/sessions','projects':'/api/projects','files':'/api/files','releases current':'/api/releases/current','A2A agent card':'/.well-known/agent-card.json'}
for name,path in paths.items():
 req=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+token})
 try:
  with urllib.request.urlopen(req,timeout=5) as res:
   body=res.read(); obj=json.loads(body) if body else None
   shape=f'items={len(obj)}' if isinstance(obj,list) else f'keys={",".join(sorted(obj)[:6])}' if isinstance(obj,dict) else type(obj).__name__
   print(f'{name}: HTTP {res.status} {shape}')
 except Exception as e: print(f'{name}: FAIL {e}')
PY
```

Output:

```text
GET /api/home                         HTTP 200 keys=counts,local_ai,needs_you,recent_notes,running,teams_running
GET /api/node-types                   HTTP 200 items=18
GET /api/environments                 HTTP 200 items=0
GET /api/runs                         HTTP 200 items=0
GET /api/vault/notes                  HTTP 200 items=0
GET /api/memory/notes                 HTTP 200 items=0
GET /api/memory/graph                 HTTP 200 keys=edges,nodes
GET /api/memory/hygiene               HTTP 200 items=0
GET /api/memory/search?q=a1&mode=keyword HTTP 200 items=0
GET /api/memory/compat                HTTP 200 keys=notes_checked,ok,problems
GET /api/assistant/settings           HTTP 200
GET /api/assistant/conversations      HTTP 200 items=0
GET /api/teams                        HTTP 200 items=0
GET /api/claims                       HTTP 200 items=0
GET /api/secrets                      HTTP 200 items=0
GET /api/system/check                 HTTP 200
GET /api/system/settings              HTTP 200
GET /api/costs                        HTTP 200
GET /api/templates                    HTTP 200 items=16
GET /api/starter                      HTTP 200
GET /api/imports                      HTTP 200 items=0
GET /api/sessions                     timed out at 5 seconds while the shared runner was loaded; server logged skipped over-long Codex session lines
GET /api/projects                     HTTP 200 items=1
GET /api/files                        HTTP 200 items=0
GET /api/releases/current             HTTP 200
GET /.well-known/agent-card.json      HTTP 200
```

This was a read-only route smoke, not proof that each write/action works. E3 and the focused test references below cover selected mutations. Empty results reflect the fresh disposable home.

### E5 — live memory write/history/undo

Against the same disposable real backend, the initial API request was:

```http
PUT /api/memory/note
Authorization: Bearer a1-audit-token
Content-Type: application/json

{"path":"notes/a1-audit.md","body":"---\ntitle: Audit note\ntags: [audit]\n---\n# Real backend audit\nLink to [[missing-note]].\n","author":"owner"}
```

Output: `HTTP 200 {"path":"notes/a1-audit.md","commit":"6ebee853"}`. `GET /api/memory/note`, `/api/memory/graph`, and `/api/memory/history` returned 200; the graph included node `notes/a1-audit` and the unresolved `missing-note` link. A second revision was saved and `POST /api/memory/undo` restored the earlier body.

Command for the successful second-revision rollback:

```sh
~/w/glacier-lean/.venv/bin/python - <<'PY'
import json, urllib.request
base='http://127.0.0.1:8765'; token='a1-audit-token'
def call(method,path,data=None):
 body=None if data is None else json.dumps(data).encode()
 req=urllib.request.Request(base+path,data=body,method=method,headers={'Authorization':'Bearer '+token,**({'Content-Type':'application/json'} if body else {})})
 with urllib.request.urlopen(req,timeout=15) as res: return res.status,json.loads(res.read() or b'null')
status,first=call('GET','/api/memory/note?path=notes%2Fa1-audit.md')
status,saved=call('PUT','/api/memory/note',{'path':'notes/a1-audit.md','body':first['body']+'\nSecond revision.\n','author':'owner'})
print('memory update:',status,'commit=',saved['commit'])
status,history=call('GET','/api/memory/history?path=notes%2Fa1-audit.md')
print('memory history:',status,'versions=',len(history))
status,undo=call('POST','/api/memory/undo',{'path':'notes/a1-audit.md'})
status,restored=call('GET','/api/memory/note?path=notes%2Fa1-audit.md')
print('memory undo/read:',status,'second_revision_removed=',not restored['body'].endswith('Second revision.\n'))
PY
```

```text
memory update: 200 commit= 573aef10
memory history: 200 versions= 2
memory undo/read: 200 second_revision_removed= True
```

An undo immediately after the first-ever save returned 404 because that note had no previous version. Undoing a subsequent revision worked.

### E6 — PH0 current tool/legacy proof

Command: `~/w/glacier-lean/.venv/bin/python bench/ph0/run_ph0.py`

Output excerpt:

```text
PASS | DBOS | dbos==3.2.0; pin=3.2.0; licence=MIT
PASS | ACP | agent-client-protocol==0.12.1; pin=0.12.1; licence=Apache-2.0
PASS | MAF workflows | ... 54 passed in 124.29s
PASS | Bifrost | ... 6 passed in 1.73s; Bifrost remains optional
PASS | AG-UI | ... 23 passed in 19.48s
PASS | sandbox/repo setup
PASS | legacy paths mapped or removed | 51 mapped entries checked
PASS | prior systems disabled | ... no Forge task launch config or legacy container orchestration files
```

This current result supersedes the older **FAIL** snapshot recorded in `docs/ACCEPTANCE.md` for 2026-10-08.

### E7 — PH10 acceptance table

Command: `flock /tmp/glacier-suite.lock ~/w/glacier-lean/.venv/bin/python bench/ph10/run_ph10.py`

Output summary:

```text
guide links and screen help        FAIL     exit 1
template manifest and review       PASS
template structure and safety      PASS
six everyday templates stand-in run PASS
template tpl-backup-check          PASS     existing stand-in harness reached verified done
template tpl-daily-report          PASS
template tpl-document-note         PASS     existing stand-in harness reached verified done
template tpl-explain-error         PASS
template tpl-folder-backup         PASS
template tpl-downloads-tidy        PASS
template tpl-inbox-triage          PASS
template tpl-meeting-tasks         PASS     existing stand-in harness reached verified done
template tpl-morning-brief         PASS     existing stand-in harness reached verified done
template tpl-nightly-job           PASS
template tpl-sub-flow-example      PASS
template tpl-test-and-fix          PASS
template tpl-web-change-watch      PASS     existing stand-in harness reached verified done
template tpl-website-monitor       PASS
template tpl-weekly-research       PASS
English/Spanish keys and placeholders PASS
Spanish screen                     PASS
flow export/import                 PASS
A2A                                PASS
MCP memory server                  PASS
ACP stand-in                       PASS
AG-UI events                       PASS
AGENTS.md                          PASS
```

The specific failure was `FAIL: guide/help links - Settings help section is not registered and rendered.` The runner exited 1. Note that current runner output now reports all 16 template rows passing, while the explanatory text in `docs/ACCEPTANCE.md` still describes only six as end-to-end.

### E8 — real assistant flow apply/history/undo

A fresh temporary `GLACIER_HOME` backend used the owner’s logged-in Codex CLI. The assistant proposed a daily automation, owner approval returned `saved: true`, `GET /api/memory/history?path=environments/make-me-a-daily-automation-that-prints-t.json` returned an `assistant` commit (`b982a66b`), and `POST /api/runs/{undo_id}/undo` returned HTTP 200. The flow was absent afterward and its history contained both the apply and undo commits. No persistent Glacier home was used.

### E9 — focused real-backend regressions

Command:

```sh
cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q \
  tests/test_assistant_chat.py::test_approved_proposal_is_saved_once_as_assistant_and_can_be_undone \
  tests/test_memory_api.py::test_undo_of_first_note_version_removes_note_and_can_be_undone \
  tests/test_core.py::test_schedule_creates_runs
```

Result: `3 passed in 15.24s`. The assistant test uses a deterministic planner stub but exercises the real backend process, API, Git history, and run undo. The scheduler case uses DBOS’s real scheduler and retains checks for two completed runs and no later runs after schedule removal.

The full touched assistant and memory modules also passed under the shared suite lock: `24 passed in 23.59s` for `tests/test_assistant_chat.py tests/test_memory_api.py`.

### E10 — Settings help checks

Commands: `~/w/glacier-lean/.venv/bin/python bench/ph10/check_docs.py`, `node glacier/web/e2e/guide_links.mjs`, and after `npm run build`, `node glacier/web/e2e/settings_help.spec.mjs`.

Results: `PASS: 16 guide pages and screen help route`; `PASS (45 bold tutorial labels found in glacier/web/src)`; `PASS: F1 opens the registered Settings help panel`.

Web prerequisites also passed: `npx tsc -b`, `node e2e/theme_lint.mjs` (`theme lint ok (49 files)`), `node scripts/check-i18n.mjs --fail` (`2 dictionaries, 809 keys`), and `npm run build`.

### E11 — current live ACP rerun

The B5 run in `evidence/live/acp_two_harnesses.md` used the real backend in a temporary home, OpenCode 1.18.35 with local `qwen3:1.7b`, and Codex ACP 2.1.1. Both harnesses completed the same `./hello.txt` task. Each was `done`; Glacier’s acceptance check and the independent file check both passed. OpenCode took 23.36 s; Codex ACP took 10.11 s.

### E12 — unresolved live-log test claim

The original live-log test is still load-sensitive. Two focused attempts to add a deterministic process gate failed because they paused the fake Codex before its next stdout line, while the backend flushes logs only after reading a line. The experimental test/helper changes were reverted. Claim: `vault/claims/2026-10-09-b5-live-log-flake.md`. The live-log acceptance was not weakened or marked fixed.

## Done checkpoint audit

The `how checked` column names the current live check where available; otherwise it names the current backend suite/module, PH0/PH10 acceptance runner, or existing evidence. E1 contains the exact full-suite command and final output. A result of PARTLY explicitly means that this card did not establish the checkpoint’s complete real-world acceptance on the current machine.

| Checkpoint / feature | How checked | Result | Evidence | Suggested fix / files |
|---|---|---|---|---|
| PH0.1 core tools | PH0 runner: dependency metadata + replacement tests | WORKS | E6 | — |
| PH0.2 shared sandbox/install | PH0 runner checked pinned setup and worktree root | WORKS | E6 | — |
| PH0.3 legacy cleanup | PH0 runner checked 51 mapped entries | WORKS | E6 | — |
| PH0.4 prior systems disabled | PH0 runner scanned tracked paths/config | WORKS | E6 | — |
| PH1.1 environment format/commit | Live save + `/api/environments` | WORKS | E3 | — |
| PH1.2 node types, crash-safe runs, schedules, approvals | Live run/approval in E3; real scheduler test in E9; live-log flake remains unresolved | PARTLY | E1, E3, E9, E12 | Resolve the live-log test under load; claim `vault/claims/2026-10-09-b5-live-log-flake.md` |
| PH1.3 canvas, run states, terminal, history, vault | Live core screen in E3; flow history and assistant apply/undo in E8/E9 | WORKS | E3, E8, E9 | — |
| PH1.4 loops/sub-flows | Live loop and sub-flow runs | WORKS | E3 | — |
| PH1.5 retries, timeouts, alerts | `tests/test_core.py` and alert/retry cases in E1 | PARTLY | E1 | Full-suite run was load-sensitive; rerun focused retry/alert acceptance in CI; `glacier/backend/tests/test_core.py`, `glacier/backend/runner.py` |
| PH1.6 graceful shutdown | `test_core.py` suite coverage; not repeated with an open live socket here | PARTLY | E1 | Repeat SIGTERM acceptance under current shared runtime; `glacier/backend/tests/test_core.py`, `glacier/backend/app.py` |
| PH1.7 Windows core | Historical owner-PC/Windows CI evidence; current host is Linux | PARTLY | NORTHSTAR PH1.7 evidence | Recheck on owner Windows PC after current changes; `glacier/backend/tests/test_windows_startup.py`, `setup/` |
| PH2.1 Codex worker | Live canvas used configured fake Codex executable | PARTLY | E3 | Run same flow with owner’s installed Codex CLI; `glacier/backend/nodes/codex.py` |
| PH2.2 local-model worker | `test_local_ai.py`/`test_local_ai_answers.py`; current system check; historical owner-machine run pending | PARTLY | E1, E6, NORTHSTAR PH2.2 evidence | Complete live offline model task on owner machine; `glacier/backend/nodes/local_ai.py`, `bench/local_models/` |
| PH2.3 gateway/fallback | `test_gateway.py`, `test_gateway_preferred.py`; live settings/check routes | PARTLY | E1, E4, E6 | Run an online/offline route swap on the owner’s second machine; `glacier/backend/gateway.py` |
| PH2.4 ACP harnesses | Stand-in plus current live OpenCode and Codex ACP proof pass | WORKS | E7, E11; `evidence/live/acp_two_harnesses.md` | — |
| PH2.5 cost/route UI | `/api/costs` returned 200 with empty fresh-home usage; UI board exercises mock | PARTLY | E2, E4 | Verify model/route/cost on a real non-empty run; `glacier/web/src/screens/RunView.tsx`, `glacier/web/src/screens/SettingsSections.tsx` |
| PH2.6 second-machine provider | Current gateway tests simulate it; physical second-machine check remains historical/pending | PARTLY | E1, NORTHSTAR PH2.6 evidence | Recheck with owner’s second machine; `glacier/backend/gateway.py`, `glacier/backend/tests/test_gateway_preferred.py` |
| PH3.1 acceptance checks | Verification tests exercise refusal of missing checks | WORKS | E1 (`tests/test_verification.py`) | — |
| PH3.2 isolated verifier/protected checks | Verification and workspace tests | WORKS | E1 (`tests/test_verification.py`, `tests/test_workspaces.py`) | — |
| PH3.3 isolated worktrees/merge queue | `tests/test_workspaces.py`, `tests/test_merge_lock.py` | WORKS | E1 | — |
| PH3.4 benchmark/dashboard | Current verification tests; metric figures are prior benchmark evidence, not recomputed here | PARTLY | E1; NORTHSTAR PH3.4 evidence | Rerun benchmark and record current rates; `bench/verification/`, dashboard route/screen |
| PH3.5 circuit breakers | Verification/claims suite | WORKS | E1 (`tests/test_verification.py`) | — |
| PH3.6 worker claim filing | Claims proof tests and MCP tools | WORKS | E1 (`tests/test_claims_proof.py`, `tests/test_mcp_interop.py`) | — |
| PH3.7 automatic claim research | Claim research tests | WORKS | E1 (`tests/test_claims_research.py`) | — |
| PH3.8 specialist routing/resume | Specialist and verification tests | WORKS | E1 (`tests/test_claims_specialist.py`, `tests/test_verification.py`) | — |
| PH3.9 proposal decisions screen | Claim APIs returned 200; screen decision flow passed against mock | PARTLY | E2, E4; E1 (`tests/test_claim_rerun.py`) | Exercise a real seeded claim through approve/reject in a disposable live home; `glacier/backend/routes/claims.py`, `glacier/web/src/screens/Claims.tsx` |
| PH4.1 vault/git/search/event log | Live note save/read/history/undo | WORKS | E5 | — |
| PH4.2 MCP memory for workers | MCP interop tests | WORKS | E1, E7 (`tests/test_mcp_interop.py`: 2 passed) | — |
| PH4.3 meaning search/index | Meaning-search tests; vector support was skipped in the full suite | PARTLY | E1 (1 skipped) | Verify sqlite-vec availability and semantic results on the supported install; `glacier/backend/memory_index.py`, `setup/requirements.txt` |
| PH4.4 map/live graph | Live graph returned note/link nodes; UI graph checks used mock | PARTLY | E2, E5 | Exercise live map rendering with populated real graph and live note event; `glacier/web/src/screens/MemoryMap.tsx` |
| PH4.7 focus/links | Link resolver tests; live graph included resolved note and unresolved link | WORKS | E1, E5 (`tests/test_memory_links_exact.py`) | — |
| PH4.8 editor/plain Markdown | Live API save/read and UI editor tests against mock; front matter normalized into metadata | PARTLY | E2, E5 | Exercise linked-note authoring through real UI; `glacier/web/src/screens/NoteEditor.tsx`, `glacier/backend/routes/memory.py` |
| PH4.9 note provenance/undo | Live history + second-revision undo in E5; first-create undo and its delete undo in E9 | WORKS | E5, E9 | — |
| PH4.10 external Markdown editor compatibility | Historical owner Zettlr check; not available on this Linux audit host | PARTLY | NORTHSTAR PH4.10 evidence | Repeat owner check after current changes; `glacier/backend/vault_compat.py`, `docs/` |
| PH4.5 event-generated status notes | Status note tests; current backend suite | WORKS | E1 (`tests/test_status_notes.py`) | — |
| PH4.6 hygiene proposals | Live `/api/memory/hygiene` returned 200 empty; hygiene tests | PARTLY | E1, E4 (`tests/test_memory_hygiene.py`) | Seed a disposable duplicate/expiry case through live UI/API; `glacier/backend/routes/hygiene.py`, `glacier/web/src/screens/MemoryCleanup.tsx` |
| PH5.1 Ask/chat stream | Prior real Ask evidence: plain reply 5/5, proposal 5/5, approval 5/5; not repeated to avoid a new model call | PARTLY | `evidence/live/ask_assistant.md`; E1 (`tests/test_assistant_chat.py`) | Repeat with current installed assistant route; `glacier/backend/routes/assistant_chat.py`, `glacier/web/src/screens/Ask.tsx` |
| PH5.2 plan + checks | Prior real Ask proposals included checks; current UI plan flow was mock-backed | PARTLY | `evidence/live/ask_assistant.md`, E2 | Validate one current live goal through proposal/edit/reject; `glacier/backend/routes/assistant.py`, `glacier/web/src/screens/Ask.tsx` |
| PH5.3 assistant-approved versioned edits | Live Codex assistant proposal, apply, history, and undo on temporary backend | WORKS | E8; E9 regression | — |
| PH5.4 layouts/run explanation | Mock UI board; live run explain tests in backend suite | PARTLY | E1 (`tests/test_run_explain.py`), E2 | Exercise plain-language explanation and detail settings against populated live runs; `glacier/web/src/screens/RunView.tsx`, `glacier/web/src/screens/SettingsSections.tsx` |
| PH5.5 templates gallery | Live `/api/templates` returned 16; PH10 runner reports all 16 template rows pass; gallery UI is mock-backed | PARTLY | E2, E4, E7 | Use a template through the real UI and verify the created flow; `glacier/web/src/screens/Templates.tsx` |
| PH6.1 ChatGPT/Claude imports | Import API listing returned 200; parser/import service tests | PARTLY | E1, E4 (`tests/test_import_service.py`) | Upload a disposable export and verify dedup/search end to end; `glacier/backend/routes/imports.py`, `glacier/web/src/screens/MemoryAdd.tsx` |
| PH6.2 coding-session mirror | `/api/sessions` exceeded a 5-second request timeout while scanning real Codex files; fixture reader tests pass | PARTLY | E1, E4 (`tests/test_session_mirror*.py`) | Reduce scan latency/parse cost and repeat on this session corpus; `glacier/backend/session_mirror.py`, `glacier/backend/session_readers/`, `glacier/backend/routes/sessions.py` |
| PH6.3 file drop/images/projects/search/rename | Live project/file listing returned 200; file/image/rename tests; UI coverage is mock-backed | PARTLY | E1, E2, E4 (`tests/test_files.py`, `tests/test_image_files.py`, `tests/test_memory_rename.py`) | Upload a disposable file/image via real screen and verify resulting note; `glacier/backend/routes/files.py`, `glacier/web/src/screens/MemoryAdd.tsx` |
| PH6.4 document/web nodes and egress | Fetch/document/search tests in real-backend suite | WORKS | E1 (`tests/test_read_document.py`, `tests/test_fetch_page.py`, `tests/test_web_search.py`) | — |
| PH7.1 per-node sandbox | Sandbox tests in backend suite; no new live unsafe command was run | WORKS | E1 (`tests/test_sandboxing.py`) | — |
| PH7.2 injection/authentication | Guard/security tests in suite; no-token HTTP behavior covered by those tests | WORKS | E1 (`tests/test_local_guard.py`, `tests/test_local_token.py`) | — |
| PH7.3 secrets/keychain/redaction | Secret-store tests; live secrets listing returned 200 empty | PARTLY | E1, E4 (`tests/test_secrets.py`) | Exercise keychain write/read/redaction with a disposable secret on supported desktop OS; `glacier/backend/secrets_store.py`, `glacier/backend/routes/secrets.py` |
| PH7.4 capability catalog | Catalog/plugin tests in backend suite; no live catalog management screen | PARTLY | E1 (`tests/test_plugins.py`) | Verify provenance UI/current digest against the running install; `glacier/backend/plugins.py`, `tools/catalog/` |
| PH7.5 rollback | Rollback tests in suite; live memory second-revision undo passed | PARTLY | E1, E5 (`tests/test_rollback.py`, `tests/test_code_undo.py`) | Repeat flow and coding-run rollback via live UI; `glacier/backend/routes/rollback.py`, `glacier/web/src/screens/RunView.tsx` |
| PH8.3 first-run starter | Live system check and starter returned 200; UI setup exercised by mock suite | PARTLY | E2, E4 (`tests/test_starter.py`) | Apply one safe starter in the disposable live home and verify resulting run; `glacier/backend/routes/starter.py`, `glacier/web/src/screens/Starter.tsx` |
| PH8.4 Linux/macOS builds | Historical CI package evidence; not built/launched in this audit | PARTLY | NORTHSTAR PH8.4 evidence | Re-run current package CI; `.github/workflows/`, `desktop/` |
| PH8.5 low-resource local models | System check/settings worked; historical local benchmark is 8/10; no live local-model task run | PARTLY | E4, NORTHSTAR PH8.5 evidence | Re-run 10-task local model benchmark on supported hardware; `bench/local_models/`, `glacier/backend/nodes/local_ai.py` |
| PH9.1 maintenance Environment | Maintenance flow tests; live project-wide maintenance run not repeated | PARTLY | E1 (`tests/test_maintenance_flow.py`), NORTHSTAR PH9.1 evidence | Re-run proposal-only flow on a clean clone and verify unchanged tree; `templates/`, `glacier/backend/tests/test_maintenance_flow.py` |
| PH9.2 feature/self-build Environment | Self-build flow tests; three successful runs are historical evidence | PARTLY | E1 (`tests/test_selfbuild_flows.py`), NORTHSTAR PH9.2 evidence | Verify another real feature run under current backend; `setup/selfbuild/`, `bench/selfbuild/` |
| PH9.3 tool discovery | Maintenance/tool discovery tests and prior proposal evidence | PARTLY | E1, NORTHSTAR PH9.3 evidence | Run current scan and inspect proposal provenance; `setup/selfbuild/maintenance.py`, `tools/scan/`, `templates/` |
| PH10.2 docs/tutorials/templates | Previous 16 template checks plus help guide checker, guide links, and F1 render spec | WORKS | E7, E10 | — |
| PH10.3 localization/offline pack | Full Spanish UI board at 1280 and 1024, i18n parity passed | WORKS | E2, E7 | — |
| PH10.4 reviewed community templates | Manifest/safety checks pass | WORKS | E1, E7 (`tests/test_template_registry.py`, `templates/test_templates.py`) | — |
| PH10.5 export/import, A2A, MCP, ACP, AG-UI, AGENTS.md | PH10 interop checks and current live two-harness ACP proof pass | WORKS | E7, E11; `evidence/live/acp_two_harnesses.md` | — |
| PH11.1 health checks/upgrade cadence | Health check components ran partly via suites/acceptance; scheduled weekly health run not observed | PARTLY | E1, E6 | Run the complete health check from a clean environment; `setup/health_check.py`, `setup/` |
| PH11.2 governance/security disclosure | Files exist in repo; this audit did not test public reporting workflow | PARTLY | NORTHSTAR PH11.2 evidence | Owner should verify current repo disclosure settings; `SECURITY.md`, `GOVERNANCE.md`, `CONTRIBUTING.md` |

## Visible app features

| Feature | How checked against the real backend | Result | Evidence | Suggested fix / files |
|---|---|---|---|---|
| Home | Live `/api/home`; screen booted in E3; broader layout/controls on mock | WORKS | E2, E3, E4 | — |
| Build interview → spec → plan → team | Live `/api/teams` read only; interview/spec/team screens and transitions in mock; backend `test_teams.py` | PARTLY | E1, E2, E4 | Exercise full current build path with configured engine; `glacier/backend/routes/teams.py`, `glacier/web/src/screens/BuildTeams.tsx` |
| Ask/chat | Live conversation/settings reads and prior live Ask proof; no new assistant model call | PARTLY | E1, E4, `evidence/live/ask_assistant.md` | Recheck current live assistant with owner’s configured route; `glacier/backend/routes/assistant_chat.py`, `glacier/web/src/screens/Ask.tsx` |
| Automations canvas | Live browser saved/run flow and streamed events; real assistant flow history/undo | WORKS | E3, E8, E9 | — |
| Triggers | Trigger UI against mock; real schedule test passes; live-log test flake remains | PARTLY | E1, E2, E9, E12 | Resolve the live-log test claim |
| Templates | Live template catalog returns 16; all template checks pass; gallery UI against mock | PARTLY | E2, E4, E7 | Apply and run a template through the real screen; `glacier/web/src/screens/Templates.tsx`, `glacier/backend/routes/templates.py` |
| Runs | Live backend command/check run, status, history, terminal output | WORKS | E3 | — |
| Approvals | Live run reached waiting; approve completed; reject skipped downstream node | WORKS | E3 | — |
| Undo | Live note revision rollback; first-create note undo and restoration; assistant flow undo | WORKS | E5, E8, E9 | — |
| Memory notes/map/add | Live save/read/history/undo and graph API; UI editor/map checks use mock | PARTLY | E2, E5 | Run editor and populated map through real UI; `glacier/web/src/screens/Memory.tsx`, `MemoryMap.tsx`, `MemoryAdd.tsx` |
| Memory cleanup | Live hygiene list returns 200 empty; cleanup UI on mock; backend hygiene tests | PARTLY | E1, E2, E4 | Seed and approve a disposable proposal through real UI; `glacier/backend/routes/hygiene.py`, `glacier/web/src/screens/MemoryCleanup.tsx` |
| Imports | Live imports list returns 200 empty; import parser tests | PARTLY | E1, E4 | Upload a fixture export to the live backend and verify dedup/search; `glacier/backend/routes/imports.py`, `glacier/web/src/screens/MemoryAdd.tsx` |
| Settings: models | Live system check/settings and assistant settings returned 200; no real model task | PARTLY | E1, E4 | Verify actual route swap/run using safe configured local engine; `glacier/backend/routes/system.py`, `glacier/web/src/screens/SettingsSections.tsx` |
| Settings: secrets | Live secret list 200 empty; keychain/redaction tests | PARTLY | E1, E4 | Perform disposable keychain round trip on supported desktop OS; `glacier/backend/routes/secrets.py`, `glacier/backend/secrets_store.py` |
| Settings: usage | Live cost endpoint 200 with empty home; UI uses mock | PARTLY | E2, E4 | Confirm non-zero real run cost/route displays; `glacier/backend/routes/costs.py`, `glacier/web/src/screens/SettingsSections.tsx` |
| Settings: updates | Live releases/current 200; update UI lifecycle in mock | PARTLY | E2, E4 | Check/install a real available update only in a disposable packaged install; `glacier/backend/routes/releases.py`, `glacier/web/src/screens/SettingsSections.tsx` |
| Settings: help | Docs checker, guide-label check, and browser F1 route/render check | WORKS | E10 | — |
| Claims | Live claims list 200 empty; claims API/backend tests and mock decisions | PARTLY | E1, E2, E4 | Create a disposable live claim and complete one decision/research action; `glacier/backend/routes/claims.py`, `glacier/web/src/screens/Claims.tsx` |
| Session mirror | Live route timed out after 5 seconds scanning actual Codex files; fixture reader tests pass | PARTLY | E1, E4 | Improve scan latency and repeat against this session tree; `glacier/backend/session_mirror.py`, `glacier/backend/session_readers/` |
| A2A | Live agent card HTTP 200; PH10 task interoperability tests pass | PARTLY | E4, E7 | Start and complete an authenticated A2A task against the running backend; `glacier/backend/a2a.py`, `glacier/backend/a2a_routes.py` |
| MCP | MCP memory interop tests pass; no separate live stdio client session in this audit | PARTLY | E1, E7 | Run a real MCP client read/write round trip on disposable vault; `glacier/backend/routes/memory.py`, `glacier/backend/mcp/` |

## Audit limits

The browser board is broad but mock-backed. The live UI exercise covers the core automation path, not every screen’s write flow. The real Ask route, external CLI/model swaps, Windows/macOS packaging, Obsidian/Zettlr, owner’s second machine, and long-run scheduling were not repeated here. These are marked PARTLY rather than inferred from a green mock screen. The real backend audit used a fresh `/tmp` home; it did not inspect or modify the owner’s persistent Glacier data.
