# Conversation imports

Glacier imports official ChatGPT and Claude export files into searchable Markdown notes under `vault/imports/<source>/`. Import writes use the author `glacier-import`; known secrets are redacted before a note is saved. Re-importing a conversation with the same content leaves it unchanged, while changed content updates its existing note.

## Import an export

Send `POST /api/imports` as JSON with `{"source":"chatgpt","path":"/path/to/export.zip"}` (or a JSON export path), or as multipart form data with `source` and `file` fields. Claude uses `source: "claude"`. Uploads are streamed into the local `GLACIER_HOME/import_sources` folder so refresh can reuse them.

`GET /api/imports` lists sources with their last import time and added, updated, and unchanged counts. The screen refresh action calls `POST /api/imports/refresh`. If `GLACIER_IMPORT_DIR` names a folder, refresh uses the newest `.zip` or `.json` export in that folder. Otherwise it retries each previously imported file location that still exists.

ZIP files are inspected without extraction. Archives with more than 10,000 files or over 512 MiB of uncompressed content are refused.
