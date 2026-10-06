# Old Glacier code map

Read-only audit of the old Glacier code on the Windows PC, done 2026-10-06. Nothing on the PC was changed.

## 1. Which copy is the primary repo

**Primary source: `C:\Users\benja\Documents\Codex\GlacierV1RuntimeR21C`**
- Latest commit 2026-10-06 11:02 (`192e036`, "PUBLIC R21C source successor with canonical CMS80; not activated"). This is the newest of all copies, and CMS80 is the last campaign report number.
- 482 tracked files. Branch `master`. Remote `origin` has no fetch URL, and its push URL is set to `DISABLED-LOCAL-TRANSPORT`. None of the old copies has a GitHub remote.
- It has the most application code (51 modules, 10,497 lines in `glacier-core/glacier`). Compared with the original checkout's `glacier-core/glacier`, 67 files are byte-identical, 9 are newer here (core, tools, objectives, objective_host, product_actions, blueprints, routing, ui_service, ui/app.js), and 1 exists only here (`objective_evidence.py`). The original has no files that R21C lacks.

**Original "home" checkout:** `C:\Users\benja\Documents\Codex\2026-10-03\glacier-step-1-foundation-setup-objective\Glacier`
- Branch `glacier-environment-ui`, 4 commits, last one 2026-10-05 09:10 (`3ff6615`). There are 210 uncommitted or untracked paths, mostly `logs\*.py` campaign helper scripts, `docs\architecture`, and `tests\temp` (275 files).
- It holds the `.venv`, `node_modules`, `build`, `dist`, `logs` and `docs\architecture` folders.
- The folder is owned by Windows user `ben/CodexSandboxOffline`, so plain `git` refuses it as "dubious ownership". The audit read it with `git -c safe.directory=*`.
- The Codex campaign runtime database lives in `GlacierCampaign20261005\.glacier\glacier.sqlite` (120 MB, plus a WAL file).

Each R-numbered folder (GlacierDevR2 … GlacierSchedulingR23D, V1RuntimeR21C) is a **one-commit snapshot repo** exported from that campaign. They form a single lineage, and each one supersedes the previous one.

## 2. Summary totals (primary repo R21C)

Line counts are physical lines. The code is very dense, averaging about 90 characters per line, and `ui/app.js` is 744 lines but 155 KB. Read the line counts with that in mind.

| Bucket | Files | Lines | Verdict |
|---|---|---|---|
| App modules `glacier-core/glacier/*.py` + `*.sql` | 51 | 10,497 | see table |
| — DELETE (a free tool replaces it) | 36 | **6,491** | |
| — DELETE-UNNEEDED (governance / bookkeeping) | 12 | **3,651** | |
| — KEEP/PORT (all partial: port the ideas and text, not the code) | 3 | **355** | |
| UI `glacier-core/glacier/ui` (app.js, style.css, desktop.css, index.html) | 4 | 890 (≈210 KB) | KEEP/PORT (visual design; rewrite in React) |
| UI assets (PNG art, pixel icons SVG, VT323 font) | 22 (6 PNG, 13 SVG, 1 TTF, 2 licence txt) | binary, ≈7.9 MB | KEEP |
| `scripts/` | 26 | 1,104 | DELETE / DELETE-UNNEEDED (all) |
| `packaging/` (PyInstaller spec, Inno Setup, entry, requirements, license texts) | 10 code/config + license tree | 2,101 | DELETE for now |
| `tests/*.py` (incl. `tests/runtime`, verify scripts) | 80 | 11,861 | see section 5 |
| `tests/ui/*.cjs` (jsdom DOM tests) | 20 | 1,953 | see section 5 |
| `docs/` (campaign reports, QA, decisions, assignments) | 128 md | 14,395 | not code; mine the vision notes, delete the rest |
| `config/` | 8 | 871 | DELETE (source-test sandbox config) |

**Bottom line:** about 10,142 of 10,497 application lines (96.6%) can go. Of the code you could keep, about 355 lines of Python and about 890 lines of UI hold ideas worth porting: the UI look and feel, the Assistant roles and prompts, and the worker "behaviour" preferences. None of it carries over as-is, because all of it is tied to the old `Core`, `Store` and `ToolEngine`.

## 3. Module table (primary repo, `glacier-core/glacier/`)

| Module | Lines | Purpose (from docstring / code) | Verdict | Replaced by / notes |
|---|---|---|---|---|
| `core.py` | 690 | Worker/task runtime: sessions, lifecycle, run, recover, checkpoint, memory finalize | DELETE | DBOS durable workflows (runs, retries, crash recovery) + MAF agents |
| `storage.py` | 212 | SQLite `Store`: transactions, event log, secret redaction | DELETE | DBOS system database + OpenTelemetry events |
| `schema.sql` | 49 | Core SQLite tables | DELETE | DBOS system tables |
| `tools.py` | 742 | `ToolEngine`: managed capabilities, permissions, shell/browser/file tools, human approvals | DELETE | MAF tools + MCP servers; DBOS durable approval waits (`recv`/`send`) |
| `tool_schema.sql` | 21 | Tool-call tables | DELETE | same |
| `adapters.py` | 362 | Codex and local-model transports with checkpoints and cancellation | DELETE | ACP (drive Codex/coding agents) + Bifrost (model calls) |
| `models.py` | 250 | Model Library (catalogue of models, local/remote checks) | DELETE | Bifrost model gateway config |
| `routing.py` | 204 | Explainable model selection and fallback | DELETE | Bifrost routing/fallback |
| `scheduling.py` | 210 | Persistent work-schedule dispatcher | DELETE | DBOS scheduled workflows |
| `native_scheduler.py` | 124 | App-owned clock for the schedule and audit dispatchers | DELETE | DBOS scheduler |
| `audit_bridge.py` | 56 | Loopback n8n trigger bridge | DELETE | DBOS schedules / plain FastAPI endpoint |
| `environments.py` | 483 | "Environment" = immutable node/edge DAG (n8n-style) composed over Core | DELETE | MAF Workflows run inside DBOS; React Flow for editing |
| `development.py` | 163 | Candidate implement/QA loop (never approves) | DELETE | MAF workflow + ACP coding agent |
| `memory.py` | 170 | Scoped memory records in SQLite (owner/project/expiry) | DELETE | Git-tracked markdown vault + SQLite FTS memory service |
| `observability.py` | 198 | Read-only event query API and severity rendering | DELETE | OpenTelemetry traces + any OTel viewer |
| `diagnostics.py` | 49 | Minimal crash metadata | DELETE | OpenTelemetry |
| `ecosystem.py` | 477 | Capability registry and discovery (MCP allowlist, skills fingerprints) | DELETE | MAF MCP tool integration |
| `catalogs.py` | 48 | Local manifest catalogs feeding the registry | DELETE | MCP server config file |
| `contracts.py` | 80 | Provider/connector/execution-backend descriptors | DELETE | MAF chat clients + MCP |
| `execution.py` | 53 | Isolated Playwright browser context | DELETE | Playwright MCP server |
| `interoperability.py` | 52 | A2A 0.3 JSON-RPC outward boundary | DELETE | MAF's built-in A2A support |
| `credential_boundary.py` | 49 | Windows DPAPI-encrypted credential handles | DELETE | Bifrost holds provider keys / `.env` / OS keyring |
| `checkpoints.py` | 137 | Sealed local recovery bundles | DELETE | git (vault) + DBOS/MAF checkpoints |
| `recovery.py` | 18 | Backup of canonical SQLite state | DELETE | git + DBOS DB backup |
| `profiles.py` | 96 | Portable "desired state" profiles import/export | DELETE | Config files in the git vault |
| `projects.py` | 200 | Project identities and path aliases | DELETE | One markdown note per project in the vault (frontmatter) |
| `worktrees.py` | 86 | Worktree references and protected additive changes | DELETE | `git worktree` driven by the ACP coding agent |
| `source_fixture_scan.py` | 87 | AST scan for credential-like fixtures | DELETE | gitleaks / detect-secrets (pre-commit) |
| `cli.py` | 331 | argparse CLI over all services | DELETE | FastAPI endpoints + DBOS CLI |
| `desktop.py` | 105 | Loopback HTTP server + WebView2 host | DELETE | FastAPI/uvicorn (pywebview only if a desktop shell is wanted) |
| `ui_service.py` | 539 | Admin UI backend API (jobs, queries) | DELETE | New thin FastAPI routes |
| `worker_service.py` | 41 | Shared worker mutations for CLI/UI | DELETE | FastAPI routes |
| `launch.py` | 23 | Entry point with sanitized startup report | DELETE | `uvicorn` entry |
| `bootstrap.py` | 56 | First-run home folder init | DELETE | FastAPI lifespan + `DBOS.launch()` (a few lines) |
| `intelligence_schema.sql` | 20 | Behaviour/runtime tables | DELETE | n/a |
| `__init__.py` | 10 | Package init (disables inherited SDK telemetry) | DELETE | n/a |
| `objectives.py` | 810 | Durable parent objectives; "child receipts are claims, never acceptance" | DELETE-UNNEEDED | receipt/claims ledger |
| `objective_evidence.py` | 974 | Owner-ingested independent reviews, report registry | DELETE-UNNEEDED | review/evidence ledger |
| `objective_host.py` | 343 | Reconciles objective items with product receipts; dispatch guards | DELETE-UNNEEDED | governance |
| `product_actions.py` | 571 | Scoped product actions with deferred-dispatch receipts, admission/denial | DELETE-UNNEEDED | governance |
| `blueprints.py` | 391 | Immutable development intake / control documents | DELETE-UNNEEDED | governance (a plain MAF workflow input replaces it) |
| `audit.py` | 299 | Intermittent provider-independent supervisor audit engine | DELETE-UNNEEDED | Optional: a reviewer step in a MAF workflow |
| `audit_schema.sql` | 28 | Audit tables | DELETE-UNNEEDED | |
| `guardian.py` | 50 | Deterministic validation service | DELETE-UNNEEDED | |
| `canonical.py` | 60 | Revisioned "shadow canonical state" digests | DELETE-UNNEEDED | git vault is the source of truth |
| `harness.py` | 53 | Federation of Glacier-owned runtime records | DELETE-UNNEEDED | |
| `campaign_schema.py` | 58 | Schema for the completion-campaign tables | DELETE-UNNEEDED | CMS campaign tooling |
| `managed_operation.py` | 14 | ToolEngine operation adapter | DELETE-UNNEEDED | |
| `assistant.py` | 50 | System Assistant: planner, researcher, builder and independent-reviewer roles with their role prompts; operation tiers (EXPLAIN … MODIFY_GLACIER) | KEEP/PORT (ideas) | Re-express as a MAF workflow; copy the role prompts |
| `intelligence.py` | 158 | Worker behaviour preferences (0–100 weights turned into instructions), extractive session summary, model swap/rollback | KEEP/PORT (partial) | Port `behavior_instructions` + behaviour meanings; swap/rollback → Bifrost |
| `config.py` | 147 | Pydantic worker config (Runtime, Context, Permissions, Memory, Behavior, Schedule, Lifecycle) | KEEP/PORT (partial) | Keep only the worker profile + `Behavior` schema; drop Permissions/Lifecycle |
| `ui/app.js`, `style.css`, `desktop.css`, `index.html` | 890 | Retro "Glacier OS" desktop UI: Assistant/Projects/Environments/Activity/System, taskbar, RAW/COMPACT/EXPANDED views, light/dark theme, F-key shortcuts | KEEP/PORT (design) | Rebuild in React; keep the CSS tokens, layout and copy as the design reference |
| `ui/assets/*.png`, `icon-*.svg`, `VT323-Regular.ttf` (+ licences) | binary | Glacier art, worker portraits, Pixelarticons (MIT), VT323 font (OFL) | KEEP | Copy as-is with licence files |

The DELETE and DELETE-UNNEEDED verdicts are judgments made against the new stack, based on each module's docstring and the function and class names in it. Each module body was not read line by line.

## 4. Scripts, packaging, config (primary repo)

- `scripts/` (26 files, 1,104 lines). Everything goes.
  - Launchers `glacier.py`, `start_desktop.py`, `start_devui.py` and `start_audit_bridge.py`: DELETE (uvicorn).
  - `ollama.ps1`: DELETE. No local models are planned for now.
  - `step9_license_inventory.py`: DELETE (pip-licenses).
  - `record_campaign_*`, `register_selfhosting_reports`, `record_selfhosting_*`, `selfhosting_checkpoint`, `commit_selfhosting_stage_a`, `step9_*_proof`, `verify_step7_*`, `ui_integrity_*`, `repair_ui_integrity`, `check_environment` and the `*_appcontrol.ps1` scripts (Windows Application Control for the unsigned build): DELETE-UNNEEDED.
- `packaging/` (PyInstaller `Glacier.spec`, Inno Setup `Glacier.iss`, `entry.py`, requirements, third-party licence copies): DELETE for now. Packaging can be redone later if a desktop installer is wanted.
- `config/` (source-test sandbox): DELETE-UNNEEDED.
- In the original checkout only: `logs\*.py` (about 150 one-off export/freeze/register_cmsNN/readback scripts, about 4,000 lines) and `logs\completion-campaign` (71 files, 8,192 lines) are CMS campaign bookkeeping, so DELETE-UNNEEDED. `tests\temp` (275 files, 28,520 lines) is scratch.

## 5. Tests (primary repo)

The test functions were counted with a regex on `def test_` and `test(`, so parametrized cases are not expanded.

- **Python tests:** 61 `test_*.py` files with **about 980 tests**, plus 2 runtime helpers and 17 `verify_*`/`smoke_*`/`collect_*` scripts that are not pytest tests.
  - **About 863 tests (88%) import only modules marked DELETE or DELETE-UNNEEDED.** They should be deleted with those modules.
  - About 117 tests are in files that also touch a KEEP/PORT module: `test_intelligence.py` (86), `test_campaign_routing.py` (15), `test_remote_scope.py` (9), `test_crystal_assets.py` (3), `test_ui_redesign_assets.py` (4). They still mostly test deleted machinery (scheduling, routing, ToolEngine). Delete them too, and write fresh tests for the ported behaviour.
  - The largest governance test files are `test_product_denial_visibility.py` (77 tests, 1,118 lines), `test_objective_failure_disposition.py` (36 tests, 1,002 lines), `test_objective_evidence.py` (26 tests, 605 lines), `test_tools.py` (58 tests) and `test_ecosystem.py` (37 tests).
- **UI tests** (`tests/ui/*.cjs`, jsdom, 20 files, **about 194 tests**):
  - About 113 of them test governance screens: owner-contract, owner-new-work, owner-initial-error, assistant-denial-visibility, objective-host-controls, development-environment-*, effect-recovery, product-actions, selfhosting, step9, campaign and integrity. Delete them.
  - About 81 test the UI shell and design: interface, redesign, retro, environment-editor, environment-redesign and persistent-assistant. They target the vanilla `app.js` DOM, so they will not run against a React rewrite. They are still useful as a written spec of the intended look and behaviour.

## 6. Glacier copies on disk

Sizes include everything (`.git`, `.venv`, `node_modules`, data). "Commits" means commits reachable from HEAD.

| Path | Size | Files | Commits | Last commit | Notes |
|---|---|---|---|---|---|
| `C:\Users\benja\Documents\Codex\2026-10-03\glacier-step-1-foundation-setup-objective\Glacier` | 4,324 MB | 57,569 | 4 | 2026-10-05 09:10 | Original checkout; .venv, node_modules, logs, 210 uncommitted paths; also has 4 nested task workspaces (2026-10-03) |
| `C:\Users\benja\Documents\Codex\GlacierCampaign20261005` | 2,660 MB | 20,042 | — | — | Codex campaign home: `.glacier\glacier.sqlite` (120 MB) + about 45 task workspace clones (2026-10-05/06) |
| `C:\Users\benja\Documents\Codex\GlacierCampaign20261006` | 19.2 MB | 738 | 1 | 2026-10-06 06:26 | One workspace `recovery-r24` |
| `...\GlacierV1RuntimeR21C` | 20.4 MB | 543 | 1 | **2026-10-06 11:02** | **PRIMARY (newest)** |
| `...\GlacierSchedulingR23D` | 20.0 MB | 628 | 1 | 2026-10-06 07:13 | |
| `...\GlacierSchedulingR23` | 26.6 MB | 680 | 1 | 2026-10-06 06:26 | |
| `...\GlacierRegistryR22` | 19.8 MB | 619 | 1 | 2026-10-06 06:03 | |
| `...\GlacierPrecisionR21B` | 19.8 MB | 618 | 1 | 2026-10-06 05:41 | |
| `...\GlacierPrecisionR21` | 19.8 MB | 614 | 1 | 2026-10-06 05:26 | |
| `...\GlacierDevelopmentR20B` | 19.7 MB | 608 | 1 | 2026-10-06 05:04 | |
| `...\GlacierDevelopmentR20` | 19.6 MB | 600 | 1 | 2026-10-06 04:34 | |
| `...\GlacierPrivacyR19` | 19.6 MB | 601 | 1 | 2026-10-06 04:10 | |
| `...\GlacierProjectionR18` | 19.4 MB | 584 | 1 | 2026-10-06 03:16 | |
| `...\GlacierRuntimeE` | 20.3 MB | 610 | 1 | 2026-10-06 03:16 | |
| `...\GlacierDenialReceiptR15` | 19.3 MB | 567 | 1 | 2026-10-06 02:08 | |
| `...\GlacierDenialReceiptR14` | 19.2 MB | 555 | 1 | 2026-10-06 01:48 | |
| `...\GlacierDenialReceiptR13` | 19.1 MB | 545 | 1 | 2026-10-06 01:23 | |
| `...\GlacierOwnerTransitionR12` | 18.9 MB | 533 | 1 | 2026-10-06 00:46 | |
| `...\GlacierOwnerContractR11` | 19.1 MB | 534 | 1 | 2026-10-06 00:13 | |
| `...\GlacierRuntimeD` | 21.6 MB | 518 | 1 | 2026-10-06 00:00 | |
| `...\GlacierOwnerContractR10` | 19.0 MB | 522 | 1 | 2026-10-05 23:30 | |
| `...\GlacierOwnerContractR9` | 18.9 MB | 514 | 1 | 2026-10-05 23:05 | |
| `...\GlacierOwnerContractR8` | 18.4 MB | 494 | 1 | 2026-10-05 22:24 | |
| `...\GlacierRuntimeC` | 25.5 MB | 503 | 1 | 2026-10-05 22:15 | |
| `...\GlacierControlBoundsR7Fix` | 18.3 MB | 480 | 1 | 2026-10-05 21:23 | |
| `...\GlacierControlBootstrapR7` | 18.2 MB | 469 | 1 | 2026-10-05 20:53 | |
| `...\GlacierDevR7B` | 18.2 MB | 463 | 1 | 2026-10-05 20:44 | |
| `...\GlacierDevR7` | 18.2 MB | 459 | 1 | 2026-10-05 20:41 | |
| `...\GlacierRuntimeR6B` | 25.1 MB | 494 | 1 | 2026-10-05 20:35 | |
| `...\GlacierRuntimeR6A` | 19.0 MB | 483 | 1 | 2026-10-05 19:55 | |
| `...\GlacierDevR6` | 18.1 MB | 451 | 1 | 2026-10-05 19:29 | |
| `...\GlacierDevR5` | 17.8 MB | 444 | 1 | 2026-10-05 19:07 | |
| `...\GlacierDevR4` | 17.8 MB | 442 | 2 | 2026-10-05 18:42 | |
| `...\GlacierDevR3` | 17.6 MB | 427 | 1 | 2026-10-05 17:53 | |
| `...\GlacierDevR2` | 17.4 MB | 406 | 1 | 2026-10-05 17:14 | |
| `...\GlacierDev20261005` | 19.3 MB | 674 | 6 | 2026-10-05 15:57 | Clone of the original checkout |
| `C:\Users\benja\glacier-lean` | 0.1 MB | 80 | 3 | 2026-10-06 14:14 | NEW repo (GitHub `benjaminanderson0802/glacier-lean`), not old code |
| `C:\Users\benja\glacier-lean-staging` | <0.1 MB | 2 | — | — | NEW, not a git repo |

`...` stands for `C:\Users\benja\Documents\Codex`. Each snapshot folder contains `glacier-core\glacier` plus docs and tests. Total old-Glacier disk use is about **7.65 GB**: about 4.3 GB in the original checkout, 2.7 GB in Campaign20261005, and about 0.67 GB across the 34 snapshot and campaign-1006 folders.

No Glacier process was running at audit time; a `Win32_Process` command-line search for "glacier" matched only the audit's own command.

## 7. Recommended deletion order

1. **Extract the keepers first** into `glacier-lean`, from R21C:
   - `ui/` assets and licences
   - `style.css` and `desktop.css` (design tokens)
   - `app.js` and `index.html` as a design reference
   - the Assistant role prompts from `assistant.py`
   - the behaviour weights and meanings from `intelligence.py`/`config.py`
   - any vision text the user wants from `docs/decisions` and `docs/architecture`

   Also decide whether anything in `GlacierCampaign20261005\.glacier\glacier.sqlite` (worker configs, memory rows) is worth exporting to the vault.
2. **Delete the superseded snapshot repos** (GlacierDevR2 … GlacierSchedulingR23D, GlacierRuntime*, GlacierDev20261005, GlacierCampaign20261006): 33 folders, about 650 MB. Each one is fully superseded by R21C, which is the final snapshot in the same lineage.
3. **Delete `GlacierCampaign20261005`** (2.7 GB of task workspaces + campaign DB), after step 1's export decision.
4. **Delete the original checkout** `...\2026-10-03\glacier-step-1-foundation-setup-objective\Glacier` (4.3 GB). Check its 210 uncommitted paths first; they appear to be only logs, docs and scratch tests. The folder is owned by the `CodexSandboxOffline` Windows user, so deleting it may need that account or an elevated shell.
5. **Last, delete R21C itself** once the new stack covers its functions. If R21C is kept as a reference for a while, prune it inside out:
   1. governance: objectives*, product_actions, blueprints, audit*, guardian, canonical, harness, campaign_schema, managed_operation, campaign/selfhosting scripts, docs/reports, and their tests
   2. scheduling and native_scheduler (replaced by DBOS)
   3. models, routing and adapters (replaced by Bifrost/ACP)
   4. memory (replaced by the vault + FTS memory service)
   5. observability and diagnostics (replaced by OTel)
   6. tools, ecosystem, catalogs, contracts, execution and interoperability (replaced by MAF + MCP)
   7. core, storage, schema, cli, desktop, ui_service, worker_service and launch (replaced by FastAPI + DBOS)
   8. packaging

## 8. Not determined / caveats

- Test counts are regex-based (pytest was not run, so parametrized cases are not expanded). "Relates to deleted modules" is based on `glacier.<module>` imports in each test file.
- The verdicts come from module docstrings and function/class names, not from reading each module in full.
- It was not checked whether any n8n workflows outside these folders call `audit_bridge`. Its docstring says n8n is optional and its existing workflows "remain intact".
- The contents of `glacier.sqlite` (what worker/memory data exists) were not inspected.
- Sizes are from summing file lengths with PowerShell. On-disk allocation may differ.
