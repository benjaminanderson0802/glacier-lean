# Live ACP proof: two real harnesses

Run date: 2026-10-07

Both flows used the same goal and command acceptance check in separate temporary workspaces. The backend, database, and workspaces were temporary. OpenCode used the local Ollama model; Codex ACP used the existing Codex login with configured model `gpt-6-luna` and low reasoning effort.

This rerun followed the ACP failure-reporting change. OpenCode selected the configured local provider/model, returned from the ACP prompt with no message, exited with status 0, emitted no stderr, and did not create the requested file. Its own local log showed the provider stream starting, but no completion or error. OpenCode's default Zen catalog lists free models, but its instructions require signing in and using an API key; that route was not tried because it needs an account. The exact local Ollama/ACP cause remains unresolved.

## opencode

- Version: 1.18.35
- License: MIT
- Goal: `Create hello.txt containing exactly: hello from glacier`
- Acceptance: `test "$(cat hello.txt)" = "hello from glacier"`
- Glacier status: `failed`
- Glacier check passed: `False`
- Independent check passed: `False`
- Elapsed: 20.24 seconds
- Route: `acp/opencode`
- Tokens in/out: 0 / 0
- Cost USD: 0.0

Raw step output (secret patterns redacted):

```text
Coding agent finished without returning a message
Process exit status: 0
```

No stderr lines were emitted by OpenCode on this run.

## codex-acp

- Version: 2.1.1
- License: Apache-2.0
- Goal: `Create hello.txt containing exactly: hello from glacier`
- Acceptance: `test "$(cat hello.txt)" = "hello from glacier"`
- Glacier status: `failed`
- Glacier check passed: `False`
- Independent check passed: `True`
- Elapsed: 10.63 seconds
- Route: `acp/codex-acp`
- Tokens in/out: 0 / 0
- Cost USD: 0.0

Raw step output (secret patterns redacted):

```text
Coding agent exited with status -15
Process exit status: -15
Error output (last 40 lines):
[SYSTEM_ERROR] Failed to publish available commands for session 01a1181d-aa9b-7451-ace7-809d4b0d1585: RequestError: Codex process has exited with code 0:
[2m2026-10-07T20:45:59.235020Z[0m [31mERROR[0m [2mcodex_app_server[0m[2m:[0m Codex could not find bubblewrap on PATH. Install bubblewrap with your OS package manager. See the sandbox prerequisites: https://developers.openai.com/codex/concepts/sandboxing#prerequisites. Codex will use the bundled bubblewrap in the meantime.
RequestError: Codex process has exited with code 0:
[2m2026-10-07T20:45:59.235020Z[0m [31mERROR[0m [2mcodex_app_server[0m[2m:[0m Codex could not find bubblewrap on PATH. Install bubblewrap with your OS package manager. See the sandbox prerequisites: https://developers.openai.com/codex/concepts/sandboxing#prerequisites. Codex will use the bundled bubblewrap in the meantime.
    at CodexAcpServer.runWithProcessCheck (file:///home/glacier/.local/lib/node_modules/@agentclientprotocol/codex-acp/dist/index.js:40038:15)
    at process.processTicksAndRejections (node:internal/process/task_queues:103:5)
    at async CodexCommands.publish (file:///home/glacier/.local/lib/node_modules/@agentclientprotocol/codex-acp/dist/index.js:35728:30)
```

The independent file check passed even though the step was marked failed. This run exposed that ACP transport cleanup can stop an already-completed adapter process; the driver's status check has since been moved inside the active ACP session, with a fake-agent regression test. The earlier live rerun reported Codex ACP `done` with both checks passing in 11.14 seconds. This second raw result is kept as observed; the proof was not run a third time.

Result: **FAIL** — both harnesses must be done and pass both checks.

## Prior W43 qwen3:1.7b direct trial — 2026-10-07

The vague task `Create hello.txt containing exactly: hello from glacier` led the model to request `/home/user/hello.txt` outside its project, which OpenCode denied. The command exited 0 without creating the file after 59.54 seconds; maximum OpenCode RSS was 585,852 KiB (about 572 MiB). The initial `free -h` record showed 7.6 GiB total and 4.0 GiB available. Ollama reported the runner using 1.7 GB and `PROCESSOR 100% GPU`; no model was pulled.
