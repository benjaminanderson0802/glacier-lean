# W54 lean audit: backend and web source

Audit date: 2026-10-07. Scope: tracked Python modules under `glacier/backend/` (excluding tests) and tracked TypeScript/TSX under `glacier/web/src/`. No product code changed.

## Drift check and acceptance

- **Phase/checkpoint:** PH0.3, “Legacy code mapped; 97% replaceable; keepers saved; old copies removed.” PH0 is already done; this is an evidence follow-up and does not claim a new checkpoint or change NORTHSTAR status.
- **Dependencies:** PH0 exit is done. No later phase exit is a prerequisite for this read-only audit.
- **Properties/metrics:** I-01 and the lean stack serve P-GOALS, P-LOOPS, P-SECURE, P-USABLE and M-TTFA/M-SURVIVE/M-SECURITY/M-PORTABLE by reducing custom surface while preserving safety and user contracts.
- **Existing tools:** Core graph UI, durable workflow/scheduling/retries, schema validation, secrets, Git, protocol servers, and document conversion already use OSS tools (see “Already using tools”).
- **Acceptance:** this committed file gives a module inventory with line counts and roles, a source-linked ranked candidate table with swap details and estimates, conservative dead-code/duplicate findings, and five ready-to-run follow-up cards. This is a documentation-only acceptance check; no tests were needed or run.

## Inventory method and limits

Counts use `wc -l` over tracked executable source files. There are 69 non-test Python files under `glacier/backend/` (10,104 lines), 30 TS/TSX files under `glacier/web/src/` (3,100 lines), total 99 files / 13,204 lines. Counts exclude tests, CSS, HTML, package/build files and `vite-env.d.ts`; file counts are the tracked code inventory, not a claim that every line can be deleted. Each module is recorded below; grouped entries share a common job.

### Backend modules (69 files; 10,104 lines)

| Module(s) | Lines | What it does |
|---|---:|---|
| `app.py` | 199 | Configures DBOS/FastAPI lifespan, routes, token and startup. |
| `runner.py` | 533 | Maps graph execution to DBOS workflows/steps; approvals, checks, retries, schedules and child flows. |
| `store.py` | 183 | Run/node state, usage, checks, workspace tables and live event broadcaster. |
| `vault.py` | 265 | Plain-file notes, Git commits/history, safe paths and keyword search. |
| `verify.py` | 81 | Acceptance check validation and execution, including JSON Schema. |
| `decider.py`, `assistant.py`, `routes/assistant_chat.py` | 81, 141, 448 | Model-backed decisions and goal-to-flow chat/planning route. |
| `gateway.py`, `nodes/ai_any.py`, `nodes/local_ai.py`, `nodes/acp_agent.py` | 248, 23, 153, 241 | Model routing/fallback and ACP/local worker adapters. |
| `claims.py`, `claims_research.py`, `claims_specialist.py` | 94, 106, 104 | Claim records, research, specialist repair and proof closure. |
| `workspaces.py`, `rollback.py` | 108, 337 | Isolated Git worktrees and evidence-based one-action undo. |
| `sandboxing.py`, `local_guard.py`, `local_token.py`, `egress.py` | 346, 132, 65, 61 | Per-step OS sandbox, local listener/request guards, and outbound URL/network checks. |
| `secrets_store.py`, `routes/secrets.py` | 94, 40 | OS keyring access, redaction and secret endpoints. |
| `memory_meta.py`, `memory_links.py`, `memory_rename.py`, `memory_hygiene.py`, `memory_context.py`, `memory_index.py`, `mem_server.py` | 78, 136, 234, 343, 36, 287, 118 | Note metadata, wiki links, rename, cleanup proposals, worker context, disposable semantic index and MCP tools. |
| `vault_compat.py`, `routes/vault_compat.py` | 162, 12 | Obsidian/Zettlr file/link compatibility scan and endpoint. |
| `files_store.py`, `routes/files.py`, `routes/imports.py`, `import_service.py`, `ocr.py` | 263, 89, 81, 258, 89 | Bounded upload, project files, document conversion, chat-export import and optional Tesseract OCR. |
| `nodes/read_document.py`, `nodes/fetch_page.py`, `nodes/web_search.py` | 134, 161, 251 | Local document conversion, guarded page fetching and configured SearXNG search. |
| `a2a.py`, `a2a_routes.py`, `agents_md.py`, `portable.py`, `plugins.py` | 132, 26, 88, 170, 64 | A2A surface, coding-agent instructions, environment import/export and plugin discovery. |
| `session_mirror.py`, `session_readers/__init__.py`, `session_readers/claude_code.py`, `session_readers/gemini.py`, `session_readers/opencode.py` | 300, 1, 197, 170, 335 | Read-only session summaries and tool-specific JSONL/JSON/SQLite readers. |
| `system_check.py`, `starter.py`, `template_registry.py` | 210, 180, 292 | Detect local capabilities, propose starter setup and list/validate/install templates. |
| `run_explain.py`, `status_notes.py`, `routes/home.py`, `routes/status.py`, `routes/explain.py`, `routes/costs.py` | 104, 109, 185, 28, 14, 53 | Human-readable run explanation/status notes, home summary, usage and related routes. |
| `shell_commands.py`, `routes/assistant.py`, `routes/claims.py`, `routes/rollback.py`, `routes/memory.py`, `routes/sessions.py`, `routes/starter.py`, `routes/system.py`, `routes/templates.py`, `routes/hygiene.py`, `routes/vault_compat.py`, `routes/imports.py`, `routes/files.py` | 45, 27, 76, 36, 270, 63, 31, 16, 34, 33, 12, 81, 89 | Command resolution and thin HTTP route modules for the services above. |

### Web modules (30 files; 3,100 lines)

| Module(s) | Lines | What it does |
|---|---:|---|
| `App.tsx`, `main.tsx`, `route.ts`, `layout.ts`, `draft.ts` | 91, 13, 23, 24, 6 | App shell, route state/navigation, shared layout rules and one-shot draft storage. |
| `api.ts` | 346 | Typed HTTP/WebSocket/AG-UI client, error handling, domain API wrappers and small display parsers. |
| `screens/Build.tsx`, `screens/GlacierNode.tsx`, `screens/TerminalPanel.tsx`, `screens/VaultView.tsx` | 545, 48, 30, 37 | Flow editor, custom React Flow node, terminal output and vault pane. |
| `screens/RunView.tsx`, `screens/Automations.tsx`, `screens/Templates.tsx` | 195, 85, 56 | Run state/history, flow list and template picker. |
| `screens/Ask.tsx`, `screens/Claims.tsx`, `screens/Home.tsx`, `screens/CommandPalette.tsx` | 173, 90, 79, 51 | Assistant chat/proposals, claim review, home priorities and command navigation. |
| `screens/Memory.tsx`, `screens/MemoryAdd.tsx`, `screens/MemoryCleanup.tsx`, `screens/MemoryMap.tsx`, `screens/NoteEditor.tsx` | 161, 139, 65, 94, 82 | Browse/search/edit/import/clean up notes and render the link graph. |
| `screens/Settings.tsx`, `screens/SettingsSections.tsx`, `screens/Starter.tsx`, `screens/Splash.tsx` | 86, 130, 71, 104 | Settings navigation, model/secret/usage/data/about panels, first-run setup and splash. |
| `ui/Pixel.tsx`, `ui/kit.tsx`, `ui/tok.ts` | 218, 53, 4 | Glacier visual identity/icons, shared layout controls, CSS token lookup. |

## Already using tools: do not duplicate

These are direct evidence against replacing custom code with another dependency: the relevant capability is already handled by a pinned free/open-source tool.

| Job | Existing tool and licence | Release / repo | Code that should remain as product glue |
|---|---|---|---|
| Durable runs, retries, schedules | DBOS Transact Python, MIT | 3.2.0 pinned in `setup/requirements.txt`; [release page](https://github.com/dbos-inc/dbos-transact-py/releases), latest visible 3.1.0 released 2026-09-24; [repo](https://github.com/dbos-inc/dbos-transact-py). | `runner.py` graph mapping and Glacier-specific approval/check/audit semantics; do not add APScheduler or Tenacity alongside it. |
| Flow graph UI | `@xyflow/react`, MIT | 12.12.0 pinned; [repo](https://github.com/xyflow/xyflow), active upstream; package version is in `glacier/web/package.json`. Release date not independently verified in this audit. | `Build.tsx` domain editor, Glacier nodes and validation. Replacing it with another canvas has no meaningful deletion estimate. |
| JSON Schema checks / API schemas | `jsonschema` MIT and Pydantic MIT | `jsonschema==4.25.1`, `pydantic==2.13.5`; [jsonschema repo](https://github.com/python-jsonschema/jsonschema), [Pydantic repo](https://github.com/pydantic/pydantic). | `verify.py` acceptance policy, response translation and flow rules. |
| OS secrets | `keyring`, MIT | 25.6.0 pinned; latest on PyPI at audit was 25.7.0 (2025-11-16); [repo](https://github.com/jaraco/keyring). | `secrets_store.py` naming, redaction and fail-closed behavior. No file-based or custom secret store should be kept as fallback. |
| Git operations | GitPython, BSD-3-Clause | 3.2.0 pinned; [repo](https://github.com/gitpython-developers/GitPython), active. | Domain transaction boundaries in vault, workspace and rollback code. Shelling out to Git for identical operations would not simplify the code. |
| Document conversion | MarkItDown, MIT | 0.1.8 pinned; [release page](https://github.com/microsoft/markitdown/releases), [repo](https://github.com/microsoft/markitdown). | Bounded child process, format allowlist and user-facing conversion error handling. |
| MCP server | MCP Python SDK, MIT | 1.30.0 pinned; [repo](https://github.com/modelcontextprotocol/python-sdk). | Glacier authorization, author validation and memory-specific tool definitions. |
| A2A | Official Python A2A SDK, Apache-2.0 | Dependency is supplied by agent stack; [repo](https://github.com/a2aproject/a2a-python). | Glacier flow-to-skill projection and install-token checks. Verify exact resolved version in lock/install metadata before any future version update. |

Note: `react-force-graph-2d` is already in `package.json` and `MemoryMap.tsx` imports it for the vault graph. It is a graph renderer, not an environment editor; it does not replace React Flow. Its license is MIT; [repo](https://github.com/vasturiano/react-force-graph).

## Ranked candidate swaps

Rank uses estimated removable lines divided by implementation/behavior risk (low risk scores best). Estimates are deliberately conservative and count only code plausibly made unnecessary; each swap needs an isolated acceptance suite before implementation. Release dates/licences below were checked on 2026-10-07. A “swap” means remove equivalent custom parser/helper code, not remove Glacier-specific service policy.

| Rank | Candidate and upstream evidence | What could be deleted / added | Risks and estimate | Lines / risk |
|---:|---|---|---|---:|
| 1 | **Obsidian link parser consolidation with `obsilink` 0.4.0**, MIT, 2026-04-17; [repo](https://github.com/chgroeling/obsilink), [PyPI release/licence](https://pypi.org/project/obsilink/). | Delete bespoke `_without_code`, wiki-link token extraction and rewriting slices in `memory_hygiene.py` and duplicated inline parsing in `vault_compat.py`; add `obsilink` as pinned parser behind a Glacier resolver adapter. Keep Glacier path ambiguity, case-folding, attachments, and Windows behavior. | New/small project, Python >=3.12 requirement must match packaged Python; its stated syntax coverage must be proven against Glacier aliases, embeds, fragments, code fences and malformed input. Possible behavior changes in rewrites. No web bundle cost. Estimate 35–65 net lines. | 65 / low-medium (0.7) |
| 2 | **CommonMark/Markdown heading parser with `markdown-it-py` 4.2.0**, MIT, 2026-05-07; [repo](https://github.com/executablebooks/markdown-it-py), [PyPI release/licence](https://pypi.org/project/markdown-it-py/). | Replace `api.ts::sections` (11 lines) with a CommonMark-aware heading/section parser if the client receives claim markdown variants; optionally consolidate Python fenced-code masking in vault checking. Add parser dependency only where Markdown is already consumed. | Most claim bodies use a tiny generated format; dependency and Python >=3.10 adds packaging cost. It parses CommonMark, not Obsidian extensions. In browser, use unified/remark instead; do not ship Python parser to web. Estimate 15–30 net lines only after tests. | 30 / low (0.8) |
| 3 | **YAML front matter handling with `python-frontmatter` 1.3.0**, MIT, 2026-05-20; [repo](https://github.com/eyeseast/python-frontmatter), [release/licence](https://pypi.org/project/python-frontmatter/). | Replace line-level YAML reading in `memory_meta.py` and `memory_hygiene.py`, and `_front_matter` extraction in `vault_compat.py` with one parser; retain service-owned field filtering, output serialization and claims protection. | PyYAML is already installed, so added dependency is arguably redundant; parser normalization can reorder/coerce values. Need preserve custom fields and service metadata exactly; likely only 20–40 net lines saved. | 40 / medium-low (0.6) |
| 4 | **React Markdown display with `react-markdown` 10.1.0**, MIT, 2026-03-07; [repo/releases](https://github.com/remarkjs/react-markdown/releases), [package metadata](https://github.com/remarkjs/react-markdown/blob/main/package.json). | Potentially replace future hand-written Markdown rendering if claim/run text is currently extended to render Markdown. As of this snapshot, there is no general Markdown renderer in `web/src`; `sections()` only extracts headings. It would add dependency and Markdown rendering capability, not remove current equivalent code. | Current actual deletion estimate is near zero; significant dependency/bundle increase, sanitization/XSS concerns and altered typography. **Not recommended as a swap now**; candidate is for a feature card only if rendered Markdown becomes a requirement. | 0 / low (0.0) |
| 5 | **APScheduler 4.x**, MIT, latest PyPI release 2026-06-28; [repo](https://github.com/agronholm/apscheduler), [release/licence](https://pypi.org/project/APScheduler/). | Would replace only scheduler syntax if DBOS were absent. In this codebase it duplicates `DBOS.create_schedule`/`delete_schedule` in `runner.py` and provides no reason to replace durable DBOS scheduling. Add nothing; recommend **no swap**. | Replacing DBOS would risk replay safety, restart behavior and duplicate runs; scheduler adds state/recovery policy and Windows service testing. Estimated custom deletion 0 because the present schedule glue remains necessary. | 0 / high (0.0) |

Additional candidates checked but not ranked as swaps: Tesseract is already the optional OCR engine; sqlite-vec is already the rebuildable semantic index; FastAPI/Starlette handle HTTP routing; SearXNG is the owner-selected search provider. No sufficiently maintained OSI package was found that safely replaces Glacier’s per-connection DNS resolution, IP checks, redirect re-checks and per-step host allowlists as a drop-in. Do not replace `egress.py`, `nodes/fetch_page.py`, or the corresponding section of `nodes/web_search.py` based on a string-only SSRF validator. `MarkItDown` and Docling are conversion options already represented; adding Docling would increase footprint rather than replace the currently configured implementation.

## Dead code and duplicate helper findings

### High-confidence dead code

None found by source import/call tracing in the audited production trees. The repository does not have `vulture` installed; checks used `rg` definition/reference searches plus route/import inspection. A function with only one caller is not dead. Dynamic entry points make plain grep insufficient: DBOS-decorated workflows/steps are called by DBOS, route modules are loaded by `plugins.py`, and MCP functions are registered inside `mem_server.main()`.

Web screen exports were cross-checked against `App.tsx` and their parent screens. `MemoryMap`, `MemoryCleanup`, `MemoryAdd`, `TerminalPanel`, and `VaultView` are live by lazy route/subtree imports; `Build` and Settings content are loaded dynamically. `vite-env.d.ts` contains only a declaration and is excluded from executable source counts. `react-force-graph-2d` is used by the live `MemoryMap.tsx`.

### Duplicated code worth removing in follow-up work

- **Markdown front matter / fenced-code masking:** `memory_links._without_code` (20 lines) duplicates `vault_compat._without_code` (20 lines); both use local regexes. `memory_hygiene._body/_metadata` (16 lines) and `vault_compat._front_matter` (12 lines) independently delimit/interpret YAML front matter. Consolidation must keep `memory_meta` service metadata semantics and compatibility diagnostics.
- **Wiki link logic:** `memory_hygiene._rewrite_links/_linked_targets` (21 lines) independently parse `[[...]]`; central `memory_links` already provides code-aware extraction and canonical resolution. Roughly 15–25 lines can be removed by adapting it, while retaining hygiene merge policy.
- **Home/state path helpers:** seven `_home()` implementations exist across import, files, hygiene, memory index, starter, template registry, secrets and local token; only some intentionally point at the vault vs app data. `import_service._state_path` and `memory_hygiene._state_path` also repeat a JSON state filename pattern. Centralize only after defining the distinct storage roots; naive consolidation risks moving files.
- **Bounded request body buffering:** `routes/files.py` and `routes/imports.py` each buffer ASGI request streams, enforce declared/actual limits and assign Starlette’s private `request._body`. A shared Starlette-supported upload helper could remove about 15–25 duplicated lines, but must preserve separate limits, errors and multipart parser behavior. Starlette is already a dependency, so no new tool is needed.
- **Session reader normalization:** Claude Code, Gemini and OpenCode readers each normalize timestamps/text and build events (two timestamp implementations, three `_text` implementations). These are similar but vendor record shapes differ. A shared internal normalization helper could remove 15–35 lines; no third-party dependency is justified.

No code was deleted in this card; each candidate is a follow-up recommendation, not authorization to modify code beyond its own card paths.

## Top five ready-to-run follow-up cards

These cards are ordered by expected lines removed per risk. Test lists name existing suites plus the new regression cases a future implementation card must add before feature work (I-03). Keep this audit document out of their paths unless the integrator assigns a separate evidence update.

### Card 1 — W54a: centralize Obsidian link parsing

- **Goal:** replace duplicate wiki-link scanning/rewriting with one maintained parser while preserving Glacier resolution, attachment, ambiguity and safe rename behavior.
- **Candidate:** `obsilink==0.4.0` (MIT, 2026-04-17, https://github.com/chgroeling/obsilink). First prove Python runtime compatibility; if package/API is insufficient, use `memory_links` as the common in-repo implementation instead of keeping two parsers.
- **Paths:** `glacier/backend/memory_links.py`, `glacier/backend/memory_hygiene.py`, `glacier/backend/vault_compat.py`, `setup/requirements.txt`, relevant backend tests.
- **Acceptance tests:** existing `tests/test_memory_links_exact.py`, `tests/test_memory_hygiene.py`, `tests/test_memory_rename.py`, `tests/test_vault_compat.py`; add coverage for fenced and inline code, `[[alias|display]]`, embeds, fragments, relative Markdown links, Windows paths, duplicate basenames, and rename/merge preservation.
- **Estimate:** 35–65 net lines removed. Risks: tool maturity, Python version, false parsing/rewrite, Windows path handling.

### Card 2 — W54b: one upload-body limiter

- **Goal:** remove duplicated ASGI body buffering and size checks while retaining the existing Starlette/FastAPI file upload behavior.
- **Paths:** `glacier/backend/routes/files.py`, `glacier/backend/routes/imports.py`, `glacier/backend/files_store.py` only if needed, `glacier/backend/tests/test_files.py`, `glacier/backend/tests/test_import_service.py`.
- **Acceptance tests:** existing file/import suites; add declared-length and chunked over-limit tests for both routes, exact-limit acceptance, multipart parsing, request cleanup, and separate user messages/status codes. Run on Windows as file streams differ.
- **Estimate:** 15–25 lines removed, no new dependency. Risks: Starlette private `_body`, multipart parser interaction, error copy changes.

### Card 3 — W54c: consolidate front matter parsing

- **Goal:** use one YAML front matter parser for note metadata, compatibility checks and hygiene, while keeping service-generated metadata and custom fields intact.
- **Candidate:** `python-frontmatter==1.3.0` (MIT, 2026-05-20, https://github.com/eyeseast/python-frontmatter); compare against already-pinned PyYAML so no unnecessary dependency is retained.
- **Paths:** `glacier/backend/memory_meta.py`, `glacier/backend/memory_hygiene.py`, `glacier/backend/vault_compat.py`, `setup/requirements.txt` only if needed, related tests.
- **Acceptance tests:** `tests/test_memory_api.py`, `tests/test_memory_hygiene.py`, `tests/test_vault_compat.py`; add CRLF, missing/malformed delimiters, empty YAML, nested custom values, metadata redaction, claims immutability and round-trip tests.
- **Estimate:** 20–40 lines removed. Risks: YAML scalar coercion/serialization changes and note metadata migration.

### Card 4 — W54d: consolidate runtime state roots

- **Goal:** remove duplicated app-data/state path code without changing where user files or secrets live.
- **Paths:** `glacier/backend/import_service.py`, `glacier/backend/memory_hygiene.py`, `glacier/backend/memory_index.py`, `glacier/backend/files_store.py`, `glacier/backend/template_registry.py`, `glacier/backend/starter.py`, `glacier/backend/secrets_store.py`, `glacier/backend/local_token.py`, new focused helper only if needed, associated tests.
- **Acceptance tests:** `tests/test_import_service.py`, `tests/test_memory_hygiene.py`, `tests/test_memory_index.py`, `tests/test_files.py`, `tests/test_template_registry.py`, `tests/test_starter.py`, `tests/test_secrets.py`, `tests/test_local_token.py`; add a matrix for GLACIER_HOME overrides, default paths, installed layout and no path collision.
- **Estimate:** 15–30 lines removed. Risks: user data relocation, startup path differences, Windows environment expansion. Must not migrate or delete data in this implementation without a separate authorized migration card.

### Card 5 — W54e: share bounded upload streaming

- **Goal:** use FastAPI/Starlette’s supported upload interfaces and one shared bounded-body routine for imports/files, eliminating private request mutation if supported by the pinned Starlette version.
- **Paths:** `glacier/backend/routes/files.py`, `glacier/backend/routes/imports.py`, `glacier/backend/app.py` only if middleware is needed, upload tests.
- **Acceptance tests:** same exact/over-limit and malformed multipart cases from W54b, plus memory-spooling behavior under a near-limit body and both Windows/Linux execution. Benchmark peak memory against current behavior before adoption.
- **Estimate:** 10–20 additional lines beyond W54b if Starlette supports it cleanly; zero new dependency. Risks: implementation depends on current request stream semantics; do not use if streaming regression or extra buffering occurs.

**Overlap note:** W54b and W54e should be merged into one implementation card by the integrator if they touch the same route files; do not run them in parallel. W54e is listed separately because removing the private `_body` assignment may be a distinct proof step from extracting the already duplicated limiter.

## Source links

- [DBOS Python releases](https://github.com/dbos-inc/dbos-transact-py/releases) and [MIT metadata](https://github.com/dbos-inc/dbos-transact-py/blob/main/pyproject.toml)
- [MarkItDown releases](https://github.com/microsoft/markitdown/releases) and [MIT licence](https://github.com/microsoft/markitdown/blob/main/LICENSE)
- [React Flow open-source licence](https://xyflow.com/open-source) and [xyflow repo](https://github.com/xyflow/xyflow)
- [keyring PyPI release/licence](https://pypi.org/project/keyring/) and [repo](https://github.com/jaraco/keyring)
- [APScheduler PyPI release/licence](https://pypi.org/project/APScheduler/) and [repo](https://github.com/agronholm/apscheduler)
- [markdown-it-py release/licence](https://pypi.org/project/markdown-it-py/) and [repo](https://github.com/executablebooks/markdown-it-py)
- [python-frontmatter release/licence](https://pypi.org/project/python-frontmatter/) and [repo](https://github.com/eyeseast/python-frontmatter)
- [Obsilink release/licence](https://pypi.org/project/obsilink/) and [repo](https://github.com/chgroeling/obsilink)
- [react-markdown release](https://github.com/remarkjs/react-markdown/releases) and [MIT package metadata](https://github.com/remarkjs/react-markdown/blob/main/package.json)
