# Runtime side effect audit

Inventory source: API decorators under `glacier/backend/routes/` and `app.py`, plus the served node catalog (`glacier/contract/node_types.json`) and node execution dispatch in `runner.py`. `tests/test_audit_coverage.py` checks the mutating route inventory against `audit_inventory.AUDITED_ROUTES` and the side effect node set against `audit_inventory.AUDITED_NODES`.

The normalized append-only audit table is `glacier_audit` in `glacier.sqlite`. Each record contains `event_type`, `who`, `what`, and `happened_at` (UTC). The `what` fields contain identifiers, safe destinations, counts and commit IDs only. Secret values, request headers and message bodies are not recorded.

| Side effect | Entry point | Audit event | Who / what / when |
|---|---|---|---|
| Vault note write / flow save | `PUT /api/environments/{env_id}`, `PUT /api/memory/note`, assistant apply, run `note` node, MCP and other vault writers | `flow.saved`, `vault.note_written` (legacy vault `write_note` event also remains) | Owner, assistant, run or worker identity; vault path and commit; UTC write time |
| Vault note undo / rename | `/api/memory/undo`, `/api/memory/rename` | `vault.note_undone`, `vault.note_renamed` | Owner; affected paths and resulting commit; UTC completion time |
| Flow restore / run undo | `/api/environments/{env_id}/restore`, `/api/runs/{run_id}/undo` | `flow.restored`, `run.undone` | Owner; flow/run identifiers, changed paths and commit; UTC completion time |
| Run start, stop, approval, rejection | API run start and approval; schedule, file/webhook trigger, assistant and claim rerun start | `run.started`, `run.approved`, `run.rejected` | Owner/assistant; environment, run, trigger source and node; UTC time |
| Flow enable/pause and save/delete | `PUT /api/environments/{env_id}` | `flow.saved` | Owner; environment, enabled state, commit; UTC save time. Delete is not exposed by the backend API. |
| Secret set/delete | `/api/secrets/{name}` | `secret.set`, `secret.deleted` | Owner; secret name only; UTC time. Values are never included. |
| Settings changes | `/api/starter/apply` | `starter.applied` | Owner; mode, selected template IDs and created environment IDs; UTC time |
| Outbound web fetch/search, HTTP step, model and agent calls | `fetch_page`, `web_search`, `http_request`, `read_document`, `codex`, `local_ai`, `acp_agent`, `decide`, assistant chat | `outbound.web_fetch`, `outbound.web_search`, `outbound.http_request`, `outbound.document_fetch`, `outbound.model_call`, `outbound.agent_call`, `assistant.model_call` | Run/assistant; step, run, destination/method or route where available; UTC time. Payloads and credentials are excluded. |
| File writes outside vault / project creation | `/api/files`, `/api/projects`, commands and workspace steps | `file.uploaded`, `project.created`, `step.command_executed` | Owner/run; file path, project/name/size or step/run and exit code; UTC time. Command text is excluded. |
| Email / notification | failed run via Apprise (including email, ntfy, Discord, desktop and webhook targets) | `notification.sent`, `notification.failed` | Runtime; run ID, channel and target count; UTC time. Target URLs are excluded. |
| Git operations / self-build merge | verified isolated workspace merge | `git.verified_merge` | Worker; environment, run, branch and merge commit; UTC time. Ordinary vault writes retain their Git commit plus `write_note` event. |
| Trigger fires | file trigger poll and authenticated webhook | `run.started` | Runtime/owner; environment, run, source and node; UTC time |
| Imports, session saves, status rebuild, hygiene and templates | corresponding mutation APIs | `memory.imported`, `memory.imports_refreshed`, `memory.session_saved`, `status.rebuilt`, `memory.hygiene_scanned`, `memory.hygiene_applied`, `memory.hygiene_rejected`, `template.reviewed`, `template.approved` | Owner; source/name/count/proposal identifiers and resulting state; UTC time |
| Claim filing/decision/rerun | `/api/claims*` | `claim.filed`, `claim.decided`, `run.started` | Owner; claim ID, kind/action/status/run; UTC time |

There is no backend API for direct flow deletion or settings editing other than first-run setup. A shell command can cause arbitrary file, network, email or Git effects that the runtime cannot infer from its command string; the audit trail records the command execution boundary, without storing command contents. User-configured node destinations are recorded at execution. Failed validation and failed API requests do not emit success events.
