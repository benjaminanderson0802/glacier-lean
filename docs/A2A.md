# Glacier and A2A

Glacier implements the A2A Protocol **1.0** JSON-RPC binding. The version is advertised as `1.0` in the Agent Card and must be sent as the `A2A-Version: 1.0` header by clients. The card is available at `/.well-known/agent-card.json` (and `/.well-known/agent.json` for older discovery clients); JSON-RPC requests go to `/a2a`.

The server supports `message/send`, `tasks/get`, and `tasks/cancel`. A `message/send` request selects one saved flow through `message.metadata.skillId`. The owner must set that flow's `share_a2a` field to `true`; all other flows stay hidden and cannot be started through A2A. The text parts of the message are joined and supplied to the flow as `{prev_output}` for its first step. A task's completed output is returned as a text artifact.

Glacier does not stream task updates. Clients poll `tasks/get`. An approval pause is reported as `input-required`; the owner can continue or reject it through Glacier's normal approval screen. Task IDs are Glacier run IDs, so the runs appear in run history and carry the `a2a` author marker.

Every card request and JSON-RPC request needs the local install token in `Authorization: Bearer <token>`. The same loopback Host and browser Origin checks used by the local engine apply. A2A is for other local agents that have been given this token; it does not expose an unauthenticated network service.

Unsupported methods return JSON-RPC error `-32601`. Invalid parameters return `-32602`; unavailable flows and tasks return `-32004`, with a plain-language message.
