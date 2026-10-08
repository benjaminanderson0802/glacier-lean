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
An approved proposal can also include `"run_now": true` to start its first run immediately; the response includes
`run_id` and `status`. Approval is required before the proposed flow is saved or run. Apply refuses a goal without acceptance checks with a plain
message explaining that a check is needed, before validating or registering a schedule. For an approved flow with checks,
apply performs the same node-type, acceptance-check, vault-path, and schedule validation as `PUT /api/environments/{id}`,
then writes the flow atomically in one git commit authored as `assistant`. The response includes a server-generated
`undo_id` UUID; use it with `POST /api/runs/{undo_id}/undo` to restore the previous state. The commit message also
includes the conversation ID for auditing. Proposals live in backend memory until they are applied or discarded, so a
restart clears unreviewed proposals.

Saved Ask conversations are stored as Markdown notes at `conversations/<uuid>.md` in the vault. The history routes are:

- `GET /api/assistant/conversations?q=words` lists conversations newest first as `{id, title, updated, messages}`. The
  `messages` field is a message count. Search is case-insensitive and requires each query word to occur in the title or
  a message. A renamed title is used when present; otherwise the title is the first question on one line, shortened to
  60 characters.
- `GET /api/assistant/conversations/{id}` returns `{id, title, messages:[{who, text, at}]}`. The speaker is `you` or
  `glacier`. Unknown Markdown sections and speaker labels are ignored, so hand edits do not prevent reading the chat.
- `POST /api/assistant/conversations/{id}/rename` accepts `{"title":"A short title"}`. Titles are trimmed and must
  contain 1–80 characters with no line breaks. Renaming writes a normal vault version; use `POST /api/memory/undo`
  with `{"path":"conversations/<uuid>.md"}` to restore its previous version. The conversation file name stays the same.

New replies append to the same note and retain its renamed title.

- `GET /api/assistant/conversations/{id}/runs` lists runs started from that conversation with `run_id`, `env_id`,
  `status`, `started_at`, and automation `name`. It returns 404 when the conversation does not exist.
- In Ask, “run my <automation name> now” matches an existing automation and presents a “Run it now?” approval card.
  A close match that could refer to more than one automation asks which one; it never starts a run on its own.
- When a chat-started run finishes, Glacier adds the plain-language explanation from the run result to the conversation
  once. Secret values are redacted before saving the note.

## Live check

Run `bench/live_ask/run_live.py` to exercise the Ask screen's HTTP request and AG-UI stream against a temporary real backend. It records reply timing, raw proposals, approval/rejection results, and plain-language errors in `evidence/live/ask_assistant.md`. That report predates the route setting below and records a Codex-only run.

Ask uses `GLACIER_ASK_ROUTE=auto|local|codex` (`auto` by default). In `auto`, Glacier uses the signed-in Codex CLI
when available; otherwise it uses the local Ollama model selected by `system_check.default_local_model()` when Ollama
is answering. If neither is ready, Ask explains how to start Ollama and install a model or sign in to Codex. `local`
and `codex` force that route. `GET /api/system/settings` includes `ask_route` and `ask_route_reason` to show the
current choice. The conversation is sent only to the selected provider; local automation plans use that same Ollama
model, and must pass the planner's normal validation with at least one acceptance check before a proposal is shown.
