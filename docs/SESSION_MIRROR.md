# Local coding-agent session mirror

Glacier reads Codex CLI JSONL session files without changing them. By default it
looks under `~/.codex/sessions`; set `GLACIER_CODEX_SESSIONS` to use another
directory. Nested date directories are scanned. The list endpoint reads a
cached summary keyed by each file's size and modification time. Session detail
streams the file, skips malformed or overlong lines with a warning, and returns
at most the newest 2,000 events. Secret values known to Glacier are redacted
from list titles, details, and saved notes.

## API

- `GET /api/sessions` lists session id, tool, start and update times, first
  user message, working folder, and whether the session changed in the last
  two minutes.
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

For example, an OpenCode reader should parse its own official local session
records into this normalized shape rather than making Codex-specific
assumptions. The route layer can then expose the same list, detail, and
save-to-memory behavior for that reader. Keep harness discovery and parsing
separate from the vault writer so additional readers do not modify source
session files.
