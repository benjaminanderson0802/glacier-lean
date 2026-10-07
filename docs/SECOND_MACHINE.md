# Use a second computer as a private model provider

Glacier can prefer an Ollama model running on another computer while it is reachable. If the computer is offline, Glacier skips it and tries the remaining free routes. The route that answers is recorded in run usage.

## Connect the computers privately

Recommended open-source options:

- **WireGuard:** configure a tunnel between the computers and use the laptop's tunnel address.
- **Headscale:** run this open-source, self-hosted coordination server with the open-source Tailscale clients on both computers.

Hosted Tailscale's personal tier is an optional alternative. Its clients are open source, but its coordination server is not.

Both options create a private network path; neither requires exposing Ollama through a public router address.

## Keep Ollama private

Install Ollama and download a model on the laptop. Bind Ollama to its private Tailscale or WireGuard address, and configure the laptop firewall to allow TCP port 11434 only from the Glacier computer's private address. Do not bind the service to a public interface, add a router port-forward, or allow port 11434 from the public internet. Check the firewall rule on both IPv4 and IPv6 if both are enabled.

From the Glacier computer, open `http://laptop.tailnet:11434/api/tags` (replace the example name with the laptop's private address). A response listing the installed models confirms private connectivity.

## Add the route

Add a route like this to `GLACIER_HOME/gateway.json`:

```json
{
  "name": "laptop",
  "base_url": "http://laptop.tailnet:11434/v1",
  "model": "qwen3:8b",
  "paid": false,
  "daily_request_cap": 0,
  "prefer_when_online": true,
  "health_url": "http://laptop.tailnet:11434/api/tags"
}
```

Keep a local free route in the list after the preferred laptop route as a fallback. Glacier checks the health URL with a 1.5 second timeout and caches the result for 30 seconds. It tries online preferred routes first, skips offline preferred routes with a log entry, then continues through the normal route order. Run usage shows which route answered.

`gateway.json` contains routing settings only. Provider keys, if needed in the future, must be read from the operating-system keychain through `secrets_store`.
