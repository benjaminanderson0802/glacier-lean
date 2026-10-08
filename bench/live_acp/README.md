# Live ACP harness proof

`run_live.py` starts a real local Glacier backend with a temporary `GLACIER_HOME`, saves one ACP worker flow per preset, and runs the same task in separate temporary workspaces:

> Create hello.txt containing exactly: hello from glacier

Glacier checks each result with `test "$(cat hello.txt)" = "hello from glacier"`. The script also runs that exact check independently, records the per-step route, token counts, cost, duration, and raw output, then writes `evidence/live/acp_two_harnesses.md`. The evidence redacts the temporary Glacier install token and common token formats.

## Prerequisites

- Run as the `glacier` user. No sudo is needed.
- Ollama listening on `127.0.0.1:11434` with `qwen3:1.7b` available.
- OpenCode 1.18.35 and `@agentclientprotocol/codex-acp` 2.1.1 installed under `$HOME/.local` (the matching licenses are MIT and Apache-2.0).
- The official Codex CLI already logged in; the adapter uses the current Codex configuration. The observed configuration for this proof is `gpt-6-luna`, low reasoning effort.
- The project `.venv` with the backend requirements installed.

The installer commands used for a per-user install are:

```sh
npm install --global --prefix "$HOME/.local" opencode-ai@1.18.35 @agentclientprotocol/codex-acp@2.1.1
export PATH="$HOME/.local/bin:$PATH"
```

## Run

From the repository root:

```sh
.venv/bin/python bench/live_acp/run_live.py --dry-run
.venv/bin/python bench/live_acp/run_live.py
```

The dry run does not look up or launch either harness. A live run returns success only when both Glacier runs finish `done` and both the backend and independent file checks pass. A failure is kept in the evidence with its raw step output. The Codex ACP adapter uses the user's existing Codex login through the official Codex CLI and never asks this script to read, print, or copy its credential.
