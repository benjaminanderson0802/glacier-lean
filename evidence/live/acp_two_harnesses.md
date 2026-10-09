# Live ACP proof: two real harnesses

Current status: **PASS** — B5 reran the real temporary-backend proof on 2026-10-09; see the final section. Earlier failed attempts are retained as history.

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

### Granite 3.3 2B (Apache-2.0)

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

## W43 corrected prompt and live two-harness proof — 2026-10-07

At the start, `free -h` showed 7.6 GiB total and 4.5 GiB available. `qwen3:1.7b` was already installed; `ollama show qwen3:1.7b --license` reports Apache-2.0. No model was pulled or removed. The 6 GiB threshold for trying `qwen3:4b` was not met, so it was skipped. The ordered sweep stopped after the first passing model; `qwen2.5-coder:3b` and `llama3.2:3b` were not tried. Ollama reported the loaded Qwen3 runner using 1.7 GB and `100% GPU`, so this host does not establish CPU-only performance.

Both ACP harnesses used the same exact file check, in separate temporary work folders. OpenCode's project config enabled `tool_call: true` for the local model.

### OpenCode ACP

- Version/license: OpenCode 1.18.35, MIT.
- Goal: `Create ./hello.txt in this project folder with exactly this content: hello from glacier. Use the relative path ./hello.txt and do not use an absolute path.`
- Glacier status: `done`; Glacier acceptance: `True`; independent check: `True`.
- Elapsed: 28.38 seconds; model runner memory: 1.7 GB (`ollama ps`).
- Route: `acp/opencode`; cost: $0.00.
- Raw output: `The file was written successfully. Is there anything else you need help with?`

### Codex ACP

- Version/license: `@agentclientprotocol/codex-acp` 2.1.1, Apache-2.0.
- Same goal and exact file check as OpenCode.
- Glacier status: `done`; Glacier acceptance: `True`; independent check: `True`.
- Elapsed: 9.66 seconds; cost: $0.00.
- Raw output: `I’ll create ./hello.txt with the exact requested text.Created ./hello.txt with exactly hello from glacier.`

### Direct OpenCode CLI checks

Each check used OpenCode 1.18.35 in a fresh temporary project folder, with the local Ollama OpenAI-compatible endpoint and `/usr/bin/time -v`. Maximum RSS below is OpenCode's process RSS and excludes the Ollama server/model runner.

First, the prompt `Create the file hello.txt in the current folder, containing exactly: hello from glacier` took 22.47 seconds and peaked at 644,488 KiB RSS. It exited 0 without creating the file:

```text
permission requested: external_directory (/current/folder/*); auto-rejecting
✗ Write /current/folder/hello.txt failed
Error: The user rejected permission to use this specific tool call.
exit status: 0
hello.txt: absent
```

Then the explicit relative-path prompt `Create ./hello.txt in this project folder with exactly this content: hello from glacier. Use the relative path ./hello.txt and do not use an absolute path.` took 29.07 seconds and peaked at 607,892 KiB RSS. It created the file with exact content:

```text
← Write hello.txt
Wrote file successfully.
FILE_CONTENT=hello from glacier
```

### Result

PH2.4's live test is met: the same goal completed through OpenCode ACP and Codex ACP, and both Glacier checks and independent checks passed. Ollama `qwen3:1.7b` (Apache-2.0) is the tested OpenCode model. Explicitly naming `./hello.txt`, enabling `tool_call: true`, and asking the model not to use an absolute path mattered; the vague “current folder” wording caused a denied out-of-project path. Earlier failed W28 and W43 attempts remain recorded above.

## B5 live rerun — 2026-10-09

Command: `PATH="$HOME/.local/bin:$PATH" ~/w/glacier-lean/.venv/bin/python bench/live_acp/run_live.py --evidence /tmp/gf-b5-acp-two-harnesses.md`. The runner used its real temporary-home Glacier backend; its generated report was reviewed and this result was added without replacing the earlier run history.

| Harness | Version | Glacier status | Glacier check | Independent check | Elapsed |
| --- | --- | --- | --- | --- | ---: |
| OpenCode | 1.18.35 (MIT) | done | pass | pass | 23.36 s |
| Codex ACP | 2.1.1 (Apache-2.0) | done | pass | pass | 10.11 s |

Both ran the same `./hello.txt` task with `test "$(cat hello.txt)" = "hello from glacier"`. OpenCode output: `The file was written successfully to the local filesystem. No further action is required.` Codex ACP output: `I’ll create ./hello.txt in the project folder with the exact requested text.Created ./hello.txt with exactly hello from glacier.` Overall result: **PASS**. No `acp_agent.py` change was needed.
