# Local engine request protection

The engine accepts state-changing browser requests only from its own loopback origin, the Tauri app origins (`tauri://localhost`, `http://tauri.localhost`, and `https://tauri.localhost`), or the Glacier development and preview screen (`http://localhost:5173`, `http://127.0.0.1:5173`, and port `4173`) when `GLACIER_DEV=1`. Set `GLACIER_DEV=1` only while running the local development screen. Other `Origin` values receive a 403 response. When `Origin` is absent, a `Sec-Fetch-Site: cross-site` request is also blocked. WebSocket connections receive the same Host and Origin checks and hostile connections close with policy code 1008.

Requests without either browser header remain allowed. This keeps curl, tests, MCP clients, and local workers usable. It also means this guard does not authenticate local processes; a per-install token is the next security step and is outside this card.

The engine rejects Host values other than `localhost` and `127.0.0.1` (with an optional port) to reduce DNS-rebinding risk. Form bodies (`application/x-www-form-urlencoded`, `multipart/form-data`, and `text/plain`) are refused on state-changing routes except `/api/files` and `/api/imports`, which accept uploads.

The existing `bench/security` runner accepts only a fixed set of probe types, so this card does not add case files outside its assigned paths. Three suggested cases for a future benchmark update are: cross-site Origin POST rejection, trusted Tauri Origin acceptance, and DNS-rebinding Host rejection. Backend acceptance coverage is in `glacier/backend/tests/test_local_guard.py`.
