# Backend safety audit

Date: 2026-10-07
Scope: `glacier/backend` routes and backend call paths for local request control, path construction, secret handling, and outbound HTTP. This is follow-up evidence for PH7.2/P-SECURE and M-SECURITY; it does not change the PH7 checkpoint status.

## Route authentication and validation

`LocalRequestGuard` is installed around the complete FastAPI app (`app.py:37-40`). It rejects non-loopback Host values, requires the install token for every `/api/*` request and the A2A endpoints, checks browser origins on state-changing requests and WebSockets, and accepts the token on WebSockets through the query string (`local_guard.py:48-97`). The discovered API routes are all under `/api` and therefore inherit this guard. The A2A routes (`/a2a`, `/.well-known/agent-card.json`, `/.well-known/agent.json`) are explicitly covered by `A2A_PATHS`.

The only route without an install token is `GET /api/health` (`app.py:43-46`), explicitly documented as a data-free liveness check. CORS preflight `OPTIONS` is also exempt so browsers can issue preflight requests; it does not execute the requested operation. No other unauthenticated route was found.

ID/path validation observed: flow IDs now pass through `runner.env_path`; status IDs reject slash and backslash; memory paths pass through `vault.safe_path` and memory writes additionally reject claims paths; template proposal IDs are 32 lowercase hex characters; assistant conversation IDs are UUID-shaped; session save paths sanitize the session ID and add a reader-generated digest. Run IDs are database identifiers, not filesystem components. The file upload project and filename validators reject separators, colons, dot names, trailing dots, Windows device names, and executable extensions.

## User-controlled path joins reviewed

| Area | Path construction and controls |
|---|---|
| Vault notes, flows, run notes, memory APIs, undo, rename | `vault.py:54-67`, `app.py:72-97`, `routes/memory.py:34-52`, `routes/rollback.py:25-33`: canonical resolution, vault containment, symlink resolution, and `.git` exclusion; environment IDs are separately restricted by `runner.py:42-45`. Fixed cross-platform `.git` matching and environment ID validation below. |
| Uploaded files and projects | `files_store.py:39-56, 179-219`; `routes/files.py:37-89`: validated names are appended beneath `GLACIER_HOME/files/<project>`; uploads use staging, bounded size, file magic checks, and collision-safe creation. No traversal found. |
| Templates | `template_registry.py:131-168, 229-260`; `routes/templates.py:27-34`: bundled manifest paths are repository-owned; imported proposal names are generated UUIDs; approval validates the UUID before joining it into pending/approved folders. No traversal found. |
| Imports and exports | `routes/imports.py:24-49`, `import_service.py:189-205`: an owner-selected local `.zip`/`.json` path is resolved and read for the explicit import action; uploaded exports are staged under Glacier home and ZIP contents are read as archive entries, not extracted to their supplied names. This is intentional file selection, not a vault path write. The endpoint can read any locally readable export path supplied by the authenticated local owner. |
| Session readers and save-to-memory | `session_mirror.py` and `session_readers/*.py`: IDs are matched against discovered session records; `routes/sessions.py:35-60` sanitizes the ID before making a vault note path and redacts the saved text. Reader roots are local paths from OS defaults or explicit environment overrides. No traversal from the route ID found. |
| Workspace and document reader | `workspaces.py:48-66`, `runner.py:42-45`, `nodes/read_document.py:47-56`: workspace paths are built from validated environment IDs; document paths are resolved and required to remain inside the workspace. The legacy web reader's proxy handling was fixed below; DNS/address pinning remains an audit follow-up. |

## Findings

| Area | File:line | Problem | Fixed? | Test name |
|---|---|---|---|---|
| Vault path checks | `glacier/backend/vault.py:54-66` | Git metadata detection searched a case-sensitive `/.git/` substring in the native resolved path. Backslash separators evade that check on Windows, and `.GIT`/`.Git` evade it on case-insensitive filesystems. | Yes | `test_git_metadata_path_check_handles_windows_separators_and_case`; `test_git_metadata_path_check_allows_ordinary_notes` |
| Flow path IDs | `glacier/backend/runner.py:42-45` | `env_path` appended unchecked IDs to a path. Slash, backslash, and drive syntax were accepted before the vault boundary check, allowing the ID to address a different location inside the vault on platforms where those separators are active. | Yes | `test_environment_file_path_rejects_non_id_path_values` |
| Secret redaction | `glacier/backend/store.py:111-118` | Acceptance-check stdout/stderr was persisted as verification evidence without passing through `secrets_store.redact`; `/api/runs/{id}` returns that evidence. | Yes | `test_acceptance_evidence_is_redacted_before_storage` |
| Outbound web request | `glacier/backend/nodes/read_document.py:64-75` | The legacy document reader used urllib's default opener, which honors environment proxy variables and could send the request through a proxy outside the configured host check. | Yes | `test_document_reader_disables_environment_proxies` |
| Outbound web request | `glacier/backend/nodes/read_document.py:19-38,64-75` | The legacy reader validates the hostname against `GLACIER_ALLOWED_HOSTS` and revalidates redirect hostnames, but does not resolve/check and pin the destination address at connect time. A listed hostname that resolves to a private/reserved address, or changes DNS between validation and connect, may bypass the address policy used by `nodes/fetch_page.py`. Not reproduced in this audit; retained as a suspected issue. | No | — |
| Model and embedding HTTP calls | `glacier/backend/gateway.py:87-108`, `nodes/local_ai.py:52-70`, `assistant.py:60-66`, `decider.py:37-45`, `memory_index.py:41-55`, `routes/assistant_chat.py:183-189,230-238` | These calls use urllib directly. Their destinations come from configured model routes or `GLACIER_OLLAMA_URL`; they do not share the page-fetch egress validator, disable proxy discovery, or re-check redirects. The configuration is owner-controlled and some routes intentionally target local/private model hosts, so whether these need a unified allow/opt-in policy requires a separate policy decision. No request was sent during this audit. | No | — |

## Secret flow review

Run node outputs are redacted before persistence and event publication (`store.py:62-79`); plugin logs and exception outputs are redacted in `runner.py:280-297`; run note templates are redacted before vault writes (`runner.py:274-278`); session list/detail/save responses redact titles, working paths, and event text (`routes/sessions.py:13-60`); run explanations redact outputs (`run_explain.py:8-10`). The missing boundary was acceptance-check evidence and is now covered by the new storage-boundary test. I found no other demonstrated secret value reaching logs, notes, run outputs, events, or error responses without redaction. Existing session-reader warnings contain file names and parse/read errors, not file contents.

## Egress review

`nodes/fetch_page.py` uses an empty `ProxyHandler`, checks allowlisted domains, rejects non-global addresses, connects to the checked address, rechecks redirects, caps redirects, and validates the final URL. The legacy `nodes/read_document.py` now disables environment proxies and its redirects remain restricted to `GLACIER_ALLOWED_HOSTS`; its lack of DNS/address pinning is listed as a suspected issue above. Model and embedding requests use configured model destinations and are listed separately because the current code does not apply the page-fetch egress policy to them.

## Audit limits

This audit was static plus targeted regression tests on the Linux shared sandbox; Windows and macOS were not run here. Cross-platform path behavior is covered with platform-independent separator/case regression cases, but no live Windows filesystem was available. No network requests were sent to external systems. The full backend suite is run separately under the shared suite lock.
