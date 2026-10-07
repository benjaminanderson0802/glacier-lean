# Local coding-agent session mirror

Glacier reads Codex CLI JSONL session files, OpenCode's local SQLite session
database, Claude Code project transcripts, and Gemini CLI chat logs without
changing any source. Codex defaults to `~/.codex/sessions`;
set `GLACIER_CODEX_SESSIONS` to use another directory. Nested date directories
are scanned. The Codex list reader keeps cached summaries keyed by each file's
size and modification time.

OpenCode defaults to its application data directory and `opencode.db`; set
`GLACIER_OPENCODE_DATA` to point at the directory containing that database.
Glacier opens the database read-only with a short timeout and closes it after
each request. A missing or locked database produces no OpenCode rows and a
warning. Malformed sessions are skipped with a warning. List summaries are
cached by database size and modification time and read only the session rows,
message metadata, and first user text part needed for the title. Detail reads
the bodies and returns at most the newest 2,000 events. Secret values known to
Glacier are redacted from list titles, details, and saved notes.

Claude Code defaults to `~/.claude/projects/<project>/<session>.jsonl`; set
`GLACIER_CLAUDE_CODE_DATA` to point at the `.claude` data directory. The reader
uses JSONL records with top-level `type`, `sessionId`, `cwd`, and `timestamp`
fields and message content blocks (`text`, `tool_use`, and `tool_result`). The
path and transcript field names match Claude Code hooks documentation current
as checked on 2026-10-07; Anthropic does not publish a stable, versioned
transcript schema, so this reader accepts the observed JSONL shape without
claiming a pinned Claude Code release.

Gemini CLI defaults to `~/.gemini`; set `GLACIER_GEMINI_DATA` to point at the
`.gemini` data directory. The reader scans automatic chat logs at
`tmp/<project_hash>/chats/*.json` and saved checkpoints in
`tmp/<project_hash>/checkpoints/` or named `tmp/<project_hash>/checkpoint-*.json`.
Google's current `main` docs describe `chats/` session logs and checkpoint
conversation JSON under the project temp directory; the documented checkpoint
commands were checked on 2026-10-07. The reader accepts the current JSON message
fields (`sessionId`, timestamps, `messages`, role/type, content, and tool
calls), plus older checkpoint wrappers with `history` or nested `chat` arrays.

Claude Code references: [Hooks reference](https://docs.anthropic.com/en/docs/claude-code/hooks)
documents `transcript_path`; see also the [official Claude Code repository](https://github.com/anthropics/claude-code).
Gemini CLI references: [session management](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/session-management.md),
[checkpointing](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/checkpointing.md),
and [the official source tree](https://github.com/google-gemini/gemini-cli/tree/main/packages/core/src).
These are current `main` documentation/source as checked on 2026-10-07, not
version-pinned releases.

## OpenCode format source

The reader follows official OpenCode tag `v1.18.34`, commit
[`aec0b9a6d8898f68f923aaf08b7306d931fd9d76`](https://github.com/anomalyco/opencode/tree/v1.18.34).
The database path is `Global.Path.data/opencode.db`, selected in
[`packages/core/src/global.ts`](https://github.com/anomalyco/opencode/blob/v1.18.34/packages/core/src/global.ts)
and [`packages/core/src/database/database.ts`](https://github.com/anomalyco/opencode/blob/v1.18.34/packages/core/src/database/database.ts).
`Global.Path.data` uses `xdg-basedir` with an `opencode` subdirectory:

- Linux: `$XDG_DATA_HOME/opencode`, or `~/.local/share/opencode` when unset.
- macOS: `$XDG_DATA_HOME/opencode` when set, otherwise
  `~/Library/Application Support/opencode`.
- Windows: `$XDG_DATA_HOME/opencode` when set, otherwise
  `%APPDATA%\\opencode`, or `~/AppData/Roaming/opencode` when unset.

The v1.18.34 schema declares `session`, `message`, and `part` in
[`packages/core/src/database/schema.gen.ts`](https://github.com/anomalyco/opencode/blob/v1.18.34/packages/core/src/database/schema.gen.ts)
and `packages/core/src/database/migration/20260127222353_familiar_lady_ursula.ts`.
The newer projection declares `session_message` in
[`packages/core/src/session/sql.ts`](https://github.com/anomalyco/opencode/blob/v1.18.34/packages/core/src/session/sql.ts).
The reader accepts both formats present in that release: legacy messages store
JSON in `message.data` with content parts in `part.data`; v2 messages store
message metadata in `session_message.data`, with content parts in `part.data`.
It does not run migrations or write to the database.

## API

- `GET /api/sessions` lists session id, tool, start and update times, first
  user message, working folder, and whether the session changed in the last
  two minutes. OpenCode, Claude Code, and Gemini CLI rows carry a `source` and
  `opencode:`, `claude-code:`, or `gemini:` ID prefix. Codex rows keep their
  existing fields without a `source` field; a row without `source` is Codex.
- `GET /api/sessions/{id}` returns the summary and ordered plain-language
  events. Unknown event types appear as `other` with their content preserved.
- `POST /api/sessions/{id}/save-to-memory` writes a Markdown note under
  `sessions/` in the vault. The source file's content digest identifies its
  version, so repeating the request for an unchanged version does not write a
  second note. The author is `glacier-mirror`.

## Adding another harness

Add a reader module for the harness's documented, local session format. Keep
the reader read-only and stream large files line by line (with a per-line size
limit). Normalize each source into the same summary fields and event types:
`user_message`, `assistant_message`, `command`, `command_output`,
`file_change`, or `other`. Preserve unknown event content as `other` so a newer
format remains inspectable. Give each session version a stable content digest
for save deduplication, and redact text with `secrets_store.redact` before
returning it or writing it to memory.

The OpenCode reader parses its official local SQLite tables into the same
normalized event types rather than making Codex-specific assumptions. Keep
harness discovery and parsing separate from the vault writer so additional
readers do not modify source session files.
