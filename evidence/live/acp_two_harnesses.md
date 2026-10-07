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
- Elapsed: 20.78 seconds
- Route: `acp/opencode`
- Tokens in/out: 0 / 0
- Cost USD: 0.0

Raw step output (secret patterns redacted):

```text
The coding agent finished without a message
```

OpenCode failure note: the ACP node exposed no message text and did not include the child process exit code or stderr in the saved step output. The next required change is better redacted ACP failure diagnostics (exit status and safe stderr) before another live attempt; this proof does not change Glacier code or guess at the underlying cause.

## codex-acp

- Version: 2.1.1
- License: Apache-2.0
- Goal: `Create hello.txt containing exactly: hello from glacier`
- Acceptance: `test "$(cat hello.txt)" = "hello from glacier"`
- Glacier status: `done`
- Glacier check passed: `True`
- Independent check passed: `True`
- Elapsed: 13.22 seconds
- Route: `acp/codex-acp`
- Tokens in/out: 0 / 0
- Cost USD: 0.0

Raw step output (secret patterns redacted):

```text
I’ll create `hello.txt` in the workspace with the exact requested contents.Created [hello.txt](/tmp/glacier-live-acp-owye0azy/workspace-codex-acp/hello.txt) with exactly `hello from glacier`.
```

Result: **FAIL** — both harnesses must be done and pass both checks.

## Prior W43 qwen3:1.7b direct trial — 2026-10-07

The vague task `Create hello.txt containing exactly: hello from glacier` led the model to request `/home/user/hello.txt` outside its project, which OpenCode denied. The command exited 0 without creating the file after 59.54 seconds; maximum OpenCode RSS was 585,852 KiB (about 572 MiB). The initial `free -h` record showed 7.6 GiB total and 4.0 GiB available. Ollama reported the runner using 1.7 GB and `PROCESSOR 100% GPU`; no model was pulled.
