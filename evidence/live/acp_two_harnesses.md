# Live ACP proof: two real harnesses

Run date: 2026-10-07

Both flows used the same goal and command acceptance check in separate temporary workspaces. The backend, database, and workspaces were temporary. OpenCode used the local Ollama model; Codex ACP used the existing Codex login with configured model `gpt-6-luna` and low reasoning effort.

## opencode

- Version: 1.18.35
- License: MIT
- Goal: `Create hello.txt containing exactly: hello from glacier`
- Acceptance: `test "$(cat hello.txt)" = "hello from glacier"`
- Glacier status: `failed`
- Glacier check passed: `False`
- Independent check passed: `False`
- Elapsed: 55.25 seconds
- Route: `acp/opencode`
- Tokens in/out: 0 / 0
- Cost USD: 0.0

Raw step output (secret patterns redacted):

```text
Coding agent finished without returning a message
Process exit status: 0
```

## codex-acp

- Version: 2.1.1
- License: Apache-2.0
- Goal: `Create hello.txt containing exactly: hello from glacier`
- Acceptance: `test "$(cat hello.txt)" = "hello from glacier"`
- Glacier status: `done`
- Glacier check passed: `True`
- Independent check passed: `True`
- Elapsed: 9.11 seconds
- Route: `acp/codex-acp`
- Tokens in/out: 0 / 0
- Cost USD: 0.0

Raw step output (secret patterns redacted):

```text
Created [hello.txt](/tmp/glacier-live-acp-jh9gaz6i/workspace-codex-acp/hello.txt) containing exactly `hello from glacier`.
```

Result: **FAIL** — both harnesses must be done and pass both checks.

## Direct OpenCode check (outside ACP)

Both commands ran as `glacier` in temporary working folders, using OpenCode 1.18.35 and the local Ollama OpenAI-compatible endpoint. Each folder contained this `opencode.json` shape, with `MODEL` replaced by the selected model in both entries:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama local",
      "options": { "baseURL": "http://127.0.0.1:11434/v1" },
      "models": { "MODEL": { "name": "MODEL", "tool_call": true } }
    }
  },
  "model": "ollama/MODEL"
}
```

The task in both runs was exactly `Create hello.txt containing exactly: hello from glacier`.

### Qwen3 1.7B

- Exact command: `cd /tmp/opencode-direct-qwen3-1.7b.DgweY4 && timeout 150 opencode run --print-logs --log-level INFO --model ollama/qwen3:1.7b "Create hello.txt containing exactly: hello from glacier"`
- Config substitutions: `MODEL` = `qwen3:1.7b`; selected model = `ollama/qwen3:1.7b`.
- Result: exit status `0`; `hello.txt` absent.
- Captured result:

````text
> build · qwen3:1.7b
✗ Write /hello.txt failed
Error: The user rejected permission to use this specific tool call.
exit status: 0
hello.txt: absent
````

OpenCode's INFO logs showed provider `ollama` and model `qwen3:1.7b`. The requested `/hello.txt` path was outside the temporary project and OpenCode denied it.

### Granite 3.3 2B

- Exact command: `cd /tmp/opencode-direct-granite3.3-2b.jEoX3M && timeout 150 opencode run --print-logs --log-level INFO --model ollama/granite3.3:2b "Create hello.txt containing exactly: hello from glacier"`
- Config substitutions: `MODEL` = `granite3.3:2b`; selected model = `ollama/granite3.3:2b`.
- Result: exit status `0`; `hello.txt` absent.
- Captured model output:

````text
Based on the task, here's the response using the 'write' tool:

```json
{
  "command": "create_file_content",
  "description": "write a file to the local filesystem.",
  "prompt": "create hello.txt containing exactly: hello from glacier",
  "subagent_type": "write",
  "parameters": {
    "content": "hello from glacier",
    "filePath": "/path/to/hello.txt"
  }
}
```

Make sure to replace "/path/to/hello.txt" with the actual file path where you'd like to create "hello.txt".
exit status: 0
hello.txt: absent
````

Granite returned an example of a tool request instead of using a file tool. Neither tested local model completed the task through the direct OpenCode CLI, so the OpenCode ACP session path was not changed. OpenCode Zen's free catalog requires an account and API key, so it was not tried.

## Prior W43 qwen3:1.7b direct trial — 2026-10-07

A less precise prompt, `Create hello.txt containing exactly: hello from glacier`, led the model to request `/home/user/hello.txt` outside its project, which OpenCode denied. The command exited 0 without creating the file after 59.54 seconds; maximum OpenCode RSS was 585,852 KiB (about 572 MiB). The initial `free -h` record showed 7.6 GiB total and 4.0 GiB available. Ollama reported the runner using 1.7 GB and `PROCESSOR 100% GPU`; no model was pulled.
