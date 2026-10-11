# Open-source integration proof

Run on 2026-10-09 in the `gf-A2` worktree on the Glacier Linux host. Temporary backend homes and flow data were used for live calls. No transcript text, session IDs, credentials, or install tokens are included here.

## Drift check and acceptance

- **Checkpoint:** PH10.5 interoperability is the closest checkpoint; it is already marked done. This owner-directed final audit adds evidence and records gaps; it does not change checkpoint status.
- **Dependencies:** PH10.5's listed implementation evidence is present. PH1 remains in progress, so this audit does not claim a phase exit.
- **Property and metric:** P-PORTABLE / M-PORTABLE, and P-MEMORY. The audit checks whether the named OSS implementations actually run through Glacier's backend.
- **Existing tools:** Reused `bench/ph0/run_ph0.py`, backend tests, `bench/live_acp/run_live.py`, the MCP SDK test, and existing live evidence. No new proof framework was justified.
- **Acceptance:** give each requested integration a reproducible result and classify it as live pass, partial, replaced/unused, or unavailable. A package pin or mock-only test is not counted as live integration proof.

## Results

| Tool/capability | Live result on this host | Evidence and limits |
|---|---|---|
| DBOS | **Pass** | The real backend was started with temporary `GLACIER_HOME` values for the A2A and model probes below; runs completed and reported acceptance verification. `PATH="$HOME/.local/bin:$PATH" .venv/bin/python bench/ph0/run_ph0.py` also passed DBOS replacement coverage: `test_core.py`, `test_local_ai.py`, and `test_acp_agent.py`, 54 passed. Installed `dbos==3.2.0`, MIT. |
| Ollama adapter | **Pass** | A real backend flow using `local_ai`, Ollama `granite3.3:2b`, and prompt `Reply exactly GLACIER_GRANITE_LIVE_OK` completed with that exact output; recorded route `local/ollama`, cost `$0.00`. Reproduce with the temporary live model harness described below. |
| ACP SDK | **Pass** | Fresh `bench/live_acp/run_live.py --evidence /tmp/a2_live_acp.md`: OpenCode 1.18.35 and Codex ACP 2.1.1 each created `hello.txt` through Glacier's real backend; Glacier's command check and a separate filesystem check both passed. SDK pin `agent-client-protocol==0.12.1`, Apache-2.0. |
| Built-in model gateway | **Pass** | A real backend `ai_any` flow routed through `gateway/granite-local` to local Granite and returned the exact expected token, cost `$0.00`. Six existing gateway tests passed in PH0. |
| Optional Bifrost | **Not installed / not exercised** | The default built-in gateway works without Bifrost. `setup/verify_tools.sh` reports Bifrost missing; `@maximhq/bifrost@1.6.3` is documented as optional, not a Glacier runtime requirement. There is no claim here that the optional service is wired end to end. |
| React Flow | **Partial** | The pinned `@xyflow/react@12.12.0` is installed (MIT) and imported by `Build.tsx`; the PH0 runner confirms pin and package metadata. The real-backend browser probe loaded Build but could not establish `/api/events` WebSocket, so it did not prove save/drag/run against the live backend. Mock E2E coverage is not a substitute. |
| xterm | **Partial** | `@xterm/xterm@6.0.0` is installed (MIT), imported by `TerminalPanel.tsx`, and the mock core E2E checks rendered command output. The same real-backend browser probe stopped at the disconnected event socket before an xterm output assertion. Live rendering remains unproven. |
| Monaco | **Unused; replaced** | `@monaco-editor/react@4.7.0` is declared but has no production import. Glacier uses the plain-text `NoteEditor`; the PH0 replacement screen check passed. Do not describe Monaco as an active editor. |
| AG-UI | **Pass as a protocol implementation; client package unused** | Glacier's own API client parses the AG-UI event stream. PH0 ran `test_assistant_chat.py` and `test_ask_local_route.py`: 23 passed. Existing [real Ask evidence](../evidence/live/ask_assistant.md) records five real-backend conversations, valid proposals, five approvals saved, and five rejections discarded. `@ag-ui/client@0.0.59` is not imported. |
| Codex session reader | **Pass for a real session** | A temporary backend was pointed at a temporary directory containing a symlink to the latest real `~/.codex/sessions` JSONL file. Authenticated `GET /api/sessions` listed one Codex row; `GET /api/sessions/{id}` returned 366 events. Only counts were printed. A default scan of all 441 Codex files exceeded the 30-second client timeout; narrowing to one actual file succeeded. |
| OpenCode session reader | **Partial** | The real backend listed 42 rows from the local `opencode.db`; an authenticated detail request returned HTTP 200 with zero events. The database is read-only. `tests/test_session_mirror.py` and `tests/test_session_mirror_more.py` cover parser fixtures, and a separate OpenCode ACP live run passed, but ACP execution is not proof of the SQLite mirror. |
| Claude Code session reader | **No live data available** | The authenticated real backend returned zero rows; `~/.claude/projects` had no JSONL sessions and `claude` was not installed. Parser behavior is covered by reader fixture tests. |
| Gemini CLI session reader | **No live data available** | The real backend returned zero rows; `~/.gemini/tmp` had no chat/checkpoint files and `gemini` was not installed. Parser behavior is covered by reader fixture tests. |
| MCP | **Pass** | `cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_mcp_interop.py` → **2 passed**. These invoke the real MCP Python client over stdio against the real `mem_server`, exercising initialize, tool discovery, write, search, read, list, history, links, claim filing, and traversal/error refusals against a temporary vault. Existing [Codex client evidence](../evidence/live/mcp_clients.md) additionally records actual Codex MCP writes and search against a temporary backend vault. |
| A2A | **Pass** | A temporary real backend advertised a shareable flow at `/.well-known/agent-card.json`; an authenticated JSON-RPC `message/send` followed by `tasks/get` completed the flow, returned `A2A_LIVE_OK`, and the run record had author `a2a` and `verified: true`. |
| Obsidian-compatible vault | **Format pass; Obsidian app not run here** | The MCP live test wrote Markdown through the real vault writer and verified Git history/search/read. The existing owner check in NORTHSTAR records the same Markdown/link format opened in Zettlr on Windows. Obsidian itself is not installed on this Linux host; compatibility follows the plain Markdown/front matter/`[[links]]` format, not a fresh Obsidian application launch. |
| Granite local model | **Pass** | `granite3.3:2b` is installed in Ollama. Through the real backend it returned the exact prompt token both via `local_ai` (`local/ollama`) and via the built-in gateway (`gateway/granite-local`); both routes reported `$0.00`. Existing ten-task model evidence scores Granite 8/10, but that benchmark is not a substitute for this live route check. |

### Live command details

The live ACP command was:

```sh
PATH="$HOME/.local/bin:$PATH" .venv/bin/python bench/live_acp/run_live.py --evidence /tmp/a2_live_acp.md
```

Result: `opencode: status=done verified=True independent=True`; `codex-acp: status=done verified=True independent=True`.

The MCP command was:

```sh
cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_mcp_interop.py
```

Result: `2 passed in 1.32s`.

Session reader parser coverage was:

```sh
cd glacier/backend && ~/w/glacier-lean/.venv/bin/python -m pytest -q tests/test_session_mirror.py tests/test_session_mirror_more.py
```

Result: `23 passed, 1 warning in 2.34s`; these use isolated fixtures and are not presented as live sessions from all four clients.

The A2A and local-model/gateway checks used short temporary Python harnesses in `/tmp` to start `uvicorn app:app` on a free loopback port, use the generated install token, create one flow, poll `/api/runs` or A2A `tasks/get`, then terminate the backend and remove the temporary home. The emitted summaries were:

```text
session_api={"rows_by_source":{"claude-code":0,"codex":1,"gemini":0,"opencode":42},"events_by_source":{"codex":366,"opencode":0}}
a2a={"discovered":true,"state":"completed","run_author":"a2a","output_marker":true,"verified":true}
ollama_adapter={"status":"done","output_exact":true,"route":"local/ollama","model":"granite3.3:2b","cost_usd":0.0}
built_in_gateway={"status":"done","output_exact":true,"route":"gateway/granite-local","model":"granite3.3:2b","cost_usd":0.0}
```

The temporary protocol checks were run with `.venv/bin/python /tmp/a2_live_protocols.py` and `.venv/bin/python /tmp/a2_live_models.py`; those helpers are not committed because the existing live ACP and PH0 runners cover their stable cases. The relevant result summaries are preserved above.

The live browser attempt used `GLACIER_WEB_DIR="$PWD/glacier/web" bash ~/tools/e2e.sh node --input-type=module -` with an inline Playwright script. Its real-backend run ended with `Timeout 15000ms exceeded` waiting for `[data-testid="ws-status"][data-connected="true"]`. The script stopped and cleaned up its temporary backend. React Flow and xterm were not counted as live passes.

`PATH="$HOME/.local/bin:$PATH" .venv/bin/python bench/ph0/run_ph0.py` returned **12/12 PASS**. It ran 54 backend worker/runtime tests, 6 gateway tests, 23 AG-UI tests, the plain-text editor replacement screen check, and package/pin checks for React Flow and xterm. Its screen check used the mock, so it does not close the live browser gap above.

## Pinned but unused packages

| Pin | Current state | What proper use would take |
|---|---|---|
| `agent-framework-core==1.19.0` | Pinned in `setup/requirements.txt`; no production `agent_framework` import. MAF workflows are replaced by DBOS and Glacier's worker adapters. | A scoped architecture decision to adopt MAF for an actual user-visible workflow, an adapter that preserves DBOS durability/approval/audit behavior, and real-backend portability and recovery evidence. Otherwise remove the stale pin in a dependency cleanup card. |
| `agent-framework-ag-ui==1.5.0` | Installed by `setup/install_tools.sh`; no production import. | Either remove the install pin or wire its supported AG-UI bridge to a MAF assistant and verify event ordering, tool approval, reconnect/error behavior against the live UI. |
| `@ag-ui/client@0.0.59` | `package.json` pin; no source import. Glacier has a native event parser. | Replace the parser in `src/api.ts` with the package transport/event handlers, preserving approval actions and reconnect/error semantics; add parity tests against the existing event contract. No user-facing gain has yet justified the second implementation. |
| `@monaco-editor/react@4.7.0` | `package.json` pin; no source import. Note editor is plain text. | Use Monaco as a controlled Markdown editor in `NoteEditor`, keep saved vault files plain Markdown, preserve `[[link` suggestions, undo and keyboard accessibility, then verify offline loading and editor behavior. |
| `@assistant-ui/react@0.15.25` | `package.json` pin; no source import found. Ask screen uses Glacier's own UI. | Build an adapter to Glacier's streaming chat and proposal approval API, then verify streaming, tool approvals, errors, accessibility and theme compatibility end to end. |

## Gaps and suggested cards

1. **A2 follow-up — live builder / event socket.** Reproduce why the browser hosted by Vite did not connect to the real backend `/api/events` socket; then run a saved command flow and assert its React Flow node state and xterm output against the real service. The real-backend probe stopped before those assertions. Keep UI changes in a separately assigned UI card.
2. **Session mirror live fixtures.** Add an owner-approved sanitized fixture capture from current OpenCode, Claude Code, and Gemini CLI versions; run list, detail, and save-to-memory through the real backend. Investigate why 42 local OpenCode summaries yielded no detail events. Include a bounded-time test for large Codex history; the unfiltered 441-file API scan timed out at 30 seconds.
3. **Optional Bifrost smoke (only if the owner wants it supported).** Install the documented pinned service in an isolated setup and run a free local route end to end through Glacier; verify shutdown, fallback, and route accounting. Bifrost is not needed by the shipped default gateway.
4. **Unused dependency cleanup / adoption decision.** Remove abandoned pins from the setup and npm manifests, or provide the specific user-facing workflow and acceptance checks that justify adopting MAF, AG-UI client, Monaco, or assistant-ui. Do not keep packages merely to make the stack table look fuller.
5. **Vault viewer check.** If proof must name Obsidian itself, run the owner-controlled vault on a host with Obsidian installed and verify front matter plus a wikilink. The backend Markdown/Git format passed here; the application was unavailable.

## Setup verifier correction

`setup/verify_tools.sh` previously piped each command through `tail`; the pipeline status was `tail`'s status, so a missing executable could be reported as successful when output existed. Reproduction: `timeout 2 sh -c 'echo simulated-error; exit 9' 2>&1 | tail -1` printed `simulated-error` with pipeline status `0`. The probe now preserves the command's exit code and prints the last output line. Running it on this host surfaced missing Gemini CLI, Rust/Cargo, Bifrost and Docling as failures instead of masking them; Codex, OpenCode, Ollama, ACP, MarkItDown, sqlite-vec, Tauri CLI and the web build reported OK. AG-UI is reported as the native client/test replacement instead of an unused `agent-framework-ag-ui` import.
