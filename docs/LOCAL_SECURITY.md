# Local engine request protection

The engine accepts state-changing browser requests only from its own loopback origin, the Tauri app origins (`tauri://localhost`, `http://tauri.localhost`, and `https://tauri.localhost`), or the Glacier development and preview screen (`http://localhost:5173`, `http://127.0.0.1:5173`, and port `4173`) when `GLACIER_DEV=1`. Dynamic development origins can be added with `GLACIER_DEV_ORIGINS`, a comma-separated list of exact `http://localhost:<port>` or `http://127.0.0.1:<port>` origins; this list is ignored unless `GLACIER_DEV=1`. Other `Origin` values receive a 403 response. When `Origin` is absent, a `Sec-Fetch-Site: cross-site` request is also blocked. WebSocket connections receive the same Host and Origin checks and hostile connections close with policy code 1008.

The supported browser development path is `cd glacier/web && npm run live`. It starts a real backend and Vite against a disposable `GLACIER_HOME`; Ctrl+C stops both and removes that temporary home. The Vite proxy adds the install token to HTTP and WebSocket requests and rewrites `Origin` to the engine's own origin. `changeOrigin` alone only updates `Host`, so without the Origin rewrite the backend sees the browser's Vite port and rejects writes unless the development allow-list is enabled. Direct non-proxied development requests may use `GLACIER_DEV=1` with the exact Vite origin in `GLACIER_DEV_ORIGINS`.

The proxy keeps the token server-side. Browser cookies do not authenticate requests: HTTP requires `Authorization: Bearer <token>`, while the WebSocket accepts that header or its `glacier-events, <token>` subprotocol. The dev proxy adds the Authorization header for both transports, so browser WebSocket code does not need to expose the token.

Requests without either browser header pass this browser check, but every `/api` call must also carry the install token (next section), so other local programs cannot use the engine without it.

The engine rejects Host values other than `localhost` and `127.0.0.1` (with an optional port) to reduce DNS-rebinding risk. Form bodies (`application/x-www-form-urlencoded`, `multipart/form-data`, and `text/plain`) are refused on state-changing routes except `/api/files` and `/api/imports`, which accept uploads.

The existing `bench/security` runner accepts only a fixed set of probe types, so this card does not add case files outside its assigned paths. Three suggested cases for a future benchmark update are: cross-site Origin POST rejection, trusted Tauri Origin acceptance, and DNS-rebinding Host rejection. Backend acceptance coverage is in `glacier/backend/tests/test_local_guard.py`.


## Install token (every API call)

The engine has zero unauthenticated API listeners. On first start it creates a random 32-byte token in
`<GLACIER_HOME>/.engine-token` (owner-only file permissions `0600` on Linux/macOS; on Windows the file sits in the
user's own profile folder, whose default permissions already limit it to that user and administrators).
`GLACIER_TOKEN` in the environment overrides the file (tests, CI, scripted setups).

- Every `/api` request needs `Authorization: Bearer <token>`. Without it, or with a wrong one, the engine answers
  401 "This request isn't from your Glacier app." The live-events WebSocket takes the same header or `?token=<token>`
  (browsers cannot set WebSocket headers), and is closed with code 1008 otherwise.
- Open without a token: `GET /api/health` (returns only `{"ok": true}`) and CORS preflight (`OPTIONS`), which carry no data.
- The token check runs after the Host / Origin checks, so a request from another website is still refused as such.
- **Desktop app:** reads or creates the same file in its data folder and injects `window.__GLACIER_TOKEN__` next to
  `window.__GLACIER_API__`; the screen (`glacier/web/src/api.ts`) sends it on every call.
- **Browser dev setup:** the Vite proxy adds the token from `GLACIER_TOKEN` or `<GLACIER_HOME or ~/.glacier>/.engine-token` to HTTP and WebSocket requests and rewrites Origin to the engine origin. `npm run live` creates an isolated temporary home and wires both processes together.
- **Command line, workers, scripts on the same machine:** `GLACIER_TOKEN=$(cat <GLACIER_HOME>/.engine-token)`.
  `setup/selfbuild/run_card.py` and `setup/demo_seed.py` read it automatically; the benchmarks start their own engine
  with a fresh token (`bench/engine_token.py`).
- Security benchmark cases `api-no-token` and `api-stolen-origin-no-token` check both refusals.
