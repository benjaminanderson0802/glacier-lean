# Conversation imports

Glacier can import official ChatGPT and Claude data exports as searchable vault notes.

- `POST /api/imports` accepts JSON with `source` (`chatgpt` or `claude`) and a local `.zip` or `.json` `path`, or a multipart form with `source` and `file`.
- ZIP imports select `conversations.json` (or another JSON file if that name is absent). ZIPs are refused above 200 MiB uncompressed or 10,000 files.
- Uploaded request bodies are limited to 200 MiB plus 64 KiB for multipart framing; uploads are saved locally so refresh can use them later.
- Imported notes are written under `imports/<source>/`, redacted, and tagged with author `glacier-import`. A conversation ID and content hash determine whether a note is added, updated, or unchanged.
- `POST /api/imports/refresh` imports the newest `.zip` or `.json` in `GLACIER_IMPORT_DIR`, when configured. Without a watched folder, it refreshes each source from its last imported file.
- `GET /api/imports` reports the last import time and counts for each imported source.
