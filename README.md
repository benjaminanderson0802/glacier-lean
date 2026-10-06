# Glacier (lean rebuild) — basics sandbox

Glacier rebuilt on existing free, open-source tools instead of a custom engine. This repo starts with the plain foundations only: no AI models, no API keys.

| Piece | Tool |
| --- | --- |
| Workflow engine (loops, approval pauses, resume) | Microsoft Agent Framework |
| Schedules and crash recovery | DBOS on SQLite |
| Shared memory | Markdown vault in git + SQLite search, served as MCP tools |
| Screen | React Flow canvas, xterm.js terminal, Monaco editor, force graph |

Run the test board: `.venv/bin/python tests/run_all.py` → writes `RESULTS.md` and `screen.png`.
To see the screen live: `cd tests/ui && npx vite preview --port 4173 --host 0.0.0.0`, then open the forwarded port 4173.
