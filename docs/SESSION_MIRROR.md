# Local coding-agent session mirror

Glacier reads Codex CLI JSONL logs without changing the source files. The default
folder is `~/.codex/sessions`; set `GLACIER_CODEX_SESSIONS` to use another
folder. Files may be nested below that directory. The API exposes session
summaries, ordered plain-language events, and a save-to-memory action. Saved
notes are redacted through Glacier's secret store and use the
`glacier-mirror` author.

## Adding another harness

Keep each harness as a small reader that turns its local, documented session
format into the shared session summary and event shapes. The reader should
stream records, tolerate malformed lines and unknown event types, and never
write to the harness's files. Register its reader in the session discovery
layer, map its conversation, command, and file-change records to the common
event types, and add small realistic fixtures plus tests. Keep the save-to-
memory path shared so every harness gets the same redaction and deduplication
behavior. OpenCode and other harnesses can be added this way without changing
the memory API or coupling the screen to their log formats.
