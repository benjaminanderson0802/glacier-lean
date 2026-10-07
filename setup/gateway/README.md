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
  },
  {
    "name": "laptop",
    "base_url": "http://laptop.tailnet:11434/v1",
    "model": "qwen3:8b",
    "paid": false,
    "daily_request_cap": 0,
    "prefer_when_online": true,
    "health_url": "http://laptop.tailnet:11434/api/tags"
  }
]
```

A cap of `0` means there is no daily request limit. Successful requests are counted by route in `gateway_usage.json`, using the current UTC date.

When a route has `prefer_when_online: true`, Glacier checks its `health_url` before a request (maximum 1.5 seconds, cached for 30 seconds). Online preferred routes are tried first. Offline routes are skipped with a log message; Glacier then tries the regular routes in their configured order. The usage entry records the route that answered.

Future API-key support must read keys from `secrets_store` (the OS keychain), never from `gateway.json`.

## Use another computer on a private network

Recommended open-source options are **WireGuard**, configured as a tunnel between both computers, or **Headscale**, a self-hosted coordination server used with the open-source Tailscale clients. Hosted Tailscale's personal tier is an optional alternative; its coordination server is not open source. Keep the laptop route `paid: false` only when it uses a model you run yourself.

On the laptop, install Ollama and download a model, then allow its port 11434 only on the private-network interface. For example, configure Ollama's `OLLAMA_HOST` to the laptop's private Tailscale/WireGuard address and add a host firewall rule that permits TCP 11434 only from the other computer's private address. Do not bind Ollama to `0.0.0.0` on a network with public access, do not forward port 11434 on the router, and do not create a public firewall allow rule. From the gateway computer, verify that `http://laptop.tailnet:11434/api/tags` opens over the private connection, then use that same private address in `base_url` and `health_url`.

Glacier does not store API keys in `gateway.json`; any future provider key must come from the operating-system keychain through `secrets_store`.
