# Local coding-agent session mirror

Glacier reads Codex CLI JSONL session files and OpenCode's local SQLite session
database without changing either source. Codex defaults to `~/.codex/sessions`;
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
  two minutes. OpenCode rows have `source: "opencode"` and an `opencode:` ID
  prefix. Codex rows keep their existing fields without a `source` field; a
  row without `source` is Codex.
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
