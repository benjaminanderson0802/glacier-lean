# Messages API

The messages API presents Glacier assistant conversations, local coding-agent sessions, and Build team tasks through one thread contract. All routes are under `/api/messages`. The backend protects them with the same per-install token as other `/api` routes.

## Thread list

`GET /api/messages/threads?q=<words>` returns an array, newest activity first:

```json
[
  {
    "id": "glacier:8df30aab-17e1-48be-a37d-62d9c7094a28",
    "source": "glacier",
    "title": "Plan a weekly report",
    "last_text": "I can help plan that.",
    "last_at": "2026-10-09T15:14:00.000+00:00",
    "unread": false,
    "can_send": true
  }
]
```

Every row has exactly these fields:

- `id`: stable thread key. Glacier is `glacier:<conversation-uuid>`; Codex is `codex:<native-session-id>`; Claude Code keeps the mirror's `claude-code:<native-session-id>` form; OpenCode and Gemini keep `opencode:<native-session-id>` and `gemini:<native-session-id>`; a Build task is `worker:<team-id>:<task-id>`.
- `source`: `glacier`, `codex`, `claude`, `opencode`, `gemini`, or `worker`. Claude Code's existing mirror prefix is retained in its thread ID while the source value is `claude`.
- `title` and `last_text`: secret-redacted plain text. Glacier and worker rows use their latest message. Active harness sessions use their latest readable event; inactive session summaries use the preview exposed by the existing reader (usually the first user message) to keep inbox refreshes bounded. The detail route reads the session transcript.
- `last_at`: latest known ISO-8601 time, or an empty string when the source has no time.
- `unread`: currently always `false`; the backend has no per-owner read cursor.
- `can_send`: true for Glacier conversations and Build tasks that are not finished or stopped, and for Codex/Claude sessions when the corresponding CLI is installed. OpenCode and Gemini are read-only.

Search is case-insensitive and matches every query word against the thread title, last text and source. Glacier's existing conversation search also searches all of its messages.

## Read messages

`GET /api/messages/threads/{id}?before=<cursor>&limit=50` returns:

```json
{
  "id": "codex:session-id",
  "messages": [
    {"id":"codex:session-id:12","from":"them","author":"Codex","text":"Done.","at":"2026-10-09T15:14:00.000+00:00","kind":"text"}
  ],
  "next_before": null
}
```

Messages are newest first. `limit` defaults to 50 and is capped at 50. `before` is an exclusive ISO-8601 timestamp or a message ID from the same thread; message IDs preserve paging when several entries share a timestamp. When a page is full, pass its `next_before` message ID to get the next page. A missing thread returns `404`.

`from` is `me`, `them`, or `system`; `author` is a readable speaker label; `kind` is `text`, `tool`, or `status`. Harness command and output events are system/tool messages. Build task output is from its worker, owner notes are from `me`, and matching team progress-log entries are system/status messages. Secrets are redacted before any message is returned.

## Send a message

`POST /api/messages/threads/{id}` accepts `{"text":"..."}` (1–20,000 characters) and returns:

```json
{"thread_id":"glacier:<uuid>","message":{"id":"...","from":"them","author":"Glacier","text":"...","at":"...","kind":"text"}}
```

- Glacier uses the existing assistant chat route. Replies are captured from its AG-UI stream, appended to that conversation by the assistant route, and broadcast as they arrive.
- Build task messages are saved as owner notes in the task state and are added to the task's future instruction context and team progress log. The write is audited. A worker already inside a running model call cannot receive a changed prompt until it starts another attempt.
- Codex resumes with `codex exec resume <session-id> <text>`; set `GLACIER_CODEX_BIN` to select a CLI executable. The captured CLI output is returned as the reply.
- Claude resumes with `claude --resume <session-id> -p <text>`; set `GLACIER_CLAUDE_BIN` to select a CLI executable. Claude threads are sendable only when that CLI is installed.
- OpenCode and Gemini sends return `403` because those mirrors are read-only. Unknown thread IDs return `404`; unavailable CLIs return `403`, a CLI failure returns `502`, and a timed-out resume returns `504`.

Only the documented Codex and Claude resume commands write to those external session stores. Other mirrored data is read-only.

## Start a thread

`POST /api/messages/threads` accepts:

```json
{"source":"glacier","text":"Help me plan a weekly report."}
```

`source` is `glacier`, `codex`, or `claude`. The response has the same `thread`, `thread_id`, and `message` fields as the mock contract:

```json
{"thread":{"id":"glacier:<uuid>","source":"glacier","title":"Help me plan a weekly report.","last_text":"...","last_at":"...","unread":false,"can_send":true},"thread_id":"glacier:<uuid>","message":{"id":"...","from":"them","author":"Glacier","text":"...","at":"...","kind":"text"}}
```

Glacier starts a normal saved assistant conversation. Codex starts with `codex exec --json <text>` and Claude with `claude -p <text> --output-format json`; each must return a native resumable session ID or the request returns `502`. The same `GLACIER_CODEX_BIN` and `GLACIER_CLAUDE_BIN` overrides apply. A missing CLI returns `403`. Other sources fail validation with `422`.

## Live updates

Use the existing authenticated `/api/events` WebSocket; no second socket is needed. Message events use these JSON shapes:

```json
{"type":"messages.thread_delta","thread_id":"glacier:<uuid>","message_id":"...","delta":"reply part"}
{"type":"messages.thread_message","thread_id":"worker:team-1:task-a","message":{"id":"...","from":"me","author":"you","text":"Please keep the patch small.","at":"...","kind":"text"}}
```

`messages.thread_delta` arrives while Glacier streams a reply. `messages.thread_message` announces an owner message immediately and a completed Glacier or CLI reply. The socket carries existing run/team events as before.
