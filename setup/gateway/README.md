# Optional Bifrost gateway

Glacier's built-in gateway reads `GLACIER_HOME/gateway.json` and sends OpenAI-compatible chat requests directly. It does not require Bifrost.

Bifrost is an optional Apache-2.0 production gateway for deployments that want a separately managed routing service, provider health checks, or centralized observability. Run it when you need those operational features; keep it stopped for a simple local setup. The sample `bifrost.config.json` mirrors the default local Ollama route. Adjust its provider entries to match the routes in `gateway.json` before running Bifrost. Glacier's built-in gateway remains the fallback and enforces its own daily route caps and paid-route policy.

Install and run Bifrost separately using its official `@maximhq/bifrost` 1.6.3 package instructions. Bifrost is not a required Glacier dependency.

A `gateway.json` entry looks like:

```json
[
  {
    "name": "local",
    "base_url": "http://localhost:11434/v1",
    "model": "qwen3:0.6b",
    "paid": false,
    "daily_request_cap": 0
  }
]
```

A cap of `0` means there is no daily request limit. Successful requests are counted by route in `gateway_usage.json`, using the current UTC date.

Future API-key support must read keys from `secrets_store` (the OS keychain), never from `gateway.json`.
