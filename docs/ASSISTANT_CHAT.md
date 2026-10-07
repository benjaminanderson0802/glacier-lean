# Assistant chat API

`POST /api/assistant/chat` accepts `{"conversation_id": "optional-id", "message": "..."}` and returns `text/event-stream`.
Each `data:` line is one JSON object with a `type` field. The stream uses AG-UI event names: `RUN_STARTED`,
`TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`, `TOOL_CALL_START`, `TOOL_CALL_ARGS`,
`TOOL_CALL_END`, `RUN_FINISHED`, and `RUN_ERROR`. A failed model response ends with `RUN_ERROR` and a plain-language
`message`.

When the request describes an automation, the assistant calls the existing planner and emits a `propose_flow` tool call.
Its arguments include a proposal `id`, proposed `flow`, explanation, and acceptance checks. Proposing never saves or runs
the flow. Chat history is kept as a plain Markdown note under `conversations/` in the vault.

`POST /api/assistant/proposals/{id}/apply` accepts `{"approve": true}` to save or `{"approve": false}` to discard.
Approval is required before the proposed flow is saved. Apply refuses a goal without acceptance checks with a plain
message explaining that a check is needed, before validating or registering a schedule. For an approved flow with checks,
apply performs the same node-type, acceptance-check, vault-path, and schedule validation as `PUT /api/environments/{id}`,
then writes the flow atomically in one git commit authored as `assistant`. The response includes a server-generated
`undo_id` UUID; use it with `POST /api/runs/{undo_id}/undo` to restore the previous state. The commit message also
includes the conversation ID for auditing. Proposals live in backend memory until they are applied or discarded, so a
restart clears unreviewed proposals.

## Live check

Run `bench/live_ask/run_live.py` to exercise the Ask screen's HTTP request and AG-UI stream against a temporary real backend. It records reply timing, raw proposals, approval/rejection results, and plain-language errors in `evidence/live/ask_assistant.md`. That report predates the route setting below and records a Codex-only run.

Ask uses `GLACIER_ASK_ROUTE=auto|local|codex` (`auto` by default). In `auto`, Glacier uses the signed-in Codex CLI
when available; otherwise it uses the local Ollama model selected by `system_check.default_local_model()` when Ollama
is answering. If neither is ready, Ask explains how to start Ollama and install a model or sign in to Codex. `local`
and `codex` force that route. `GET /api/system/settings` includes `ask_route` and `ask_route_reason` to show the
current choice. The conversation is sent only to the selected provider; local automation plans use that same Ollama
model, and must pass the planner's normal validation with at least one acceptance check before a proposal is shown.
