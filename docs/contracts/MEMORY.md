# Contract: Memory v2 (frozen for wave 1; changes only through the integrator)

Memory = plain markdown files in GLACIER_HOME/vault, one git commit per change (rules I-06). Any database is a rebuildable index.

## Note metadata (front matter, written by the memory service, never trusted from callers)
```
---
title: <first heading or file name>
author: owner | worker:<model> | run:<run_id>
run_id: <run id or empty>
created: <ISO-8601 UTC>
updated: <ISO-8601 UTC>
tags: [a, b]
---
```
Links: `[[path/without/.md]]` or `[[path|label]]`. Tags: `#tag` in the body or `tags:` above.

## HTTP API (route plug-in glacier/backend/routes/memory.py)
- GET  /api/memory/notes?tag=&author=            -> [{path, title, author, updated, tags}]
- GET  /api/memory/note?path=                    -> {path, body, meta, links_out: [path], links_in: [path]}
- PUT  /api/memory/note  {path, body, author}    -> {path, commit}       (author must be "owner" from the screen)
- GET  /api/memory/graph                         -> {nodes: [{id, title, kind: note|run|flow|claim, author}], edges: [{source, target, kind: link|wrote}]}
- GET  /api/memory/history?path=                 -> [{commit, author, date, message}]
- POST /api/memory/undo  {path, commit?}         -> {path, commit}      (restores the version before `commit`, default: before the latest)
- GET  /api/memory/search?q=&mode=keyword|meaning -> [{path, title, score, snippet}]  (meaning falls back to keyword if no index)
Old /api/vault/* routes stay until the screen moves over.

## Live events (WS /api/events)
Memory changes: `{"type": "memory", "path", "change": "created|updated|deleted", "author", "run_id"}`.
Run-step events keep their current shape (no "type" field means a step event).

## Context for workers
Workers read memory through the MCP server (tools: search, read_note, write_note, links) and get up to 5 relevant notes injected into their prompt under "Relevant notes:" (search by the step's prompt). Writes by a worker are authored `worker:<model>` with the run id.
