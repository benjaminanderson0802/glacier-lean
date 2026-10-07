# Live same-goal harness proof — 2026-10-07

## Setup and command

OpenCode was configured from `setup/harnesses/opencode.ollama.example.json` as `/tmp/w11-live-opencode/opencode.json`; it selects local Ollama `qwen3:0.6b` at `http://127.0.0.1:11434/v1`. OpenCode `1.18.35` passed `setup/harnesses/verify_opencode.sh`. The temporary backend ran at `http://127.0.0.1:8421` with isolated `GLACIER_HOME=/tmp/w11-live-local-ai`.

The same goal was run through each harness separately using the card script:

```sh
GLACIER_PYTHON=/workspaces/glacier-lean/.venv/bin/python GLACIER_URL=http://127.0.0.1:8421 setup/harnesses/same_goal.sh opencode
GLACIER_PYTHON=/workspaces/glacier-lean/.venv/bin/python GLACIER_URL=http://127.0.0.1:8421 setup/harnesses/same_goal.sh codex-acp
```

Both script invocations completed with an independent `hello.txt == hi` assertion.

## OpenCode — PASS

The run created `hello.txt` containing exactly `hi`. Final script output:

```text
opencode: agent output: Created `hello.txt` containing exactly `hi` (2 bytes, no trailing newline).
opencode: PASS — hello.txt contains hi
```

Glacier run ID `33fd30bd8ec7`: `status: done`, `route: acp/opencode`. The script uses a separate temp directory and performs the acceptance assertion after the API run; therefore the API response has `verified: null` rather than a saved verification entry. The script exited successfully only after checking the file contents.

## Codex ACP — PASS, with a sandbox variation

The repeated script invocation created the file and passed the same independent check. Final script output:

```text
codex-acp: agent output: I’ll create the file in the workspace with the exact contents requested.The shell sandbox failed before writing the file, so I’m using the workspace file-edit mechanism to create it.Created [hello.txt](/tmp/tmp.WKahrnwFHt/codex-acp/hello.txt) with the contents `hi`.
codex-acp: PASS — hello.txt contains hi
```

Glacier run ID `0d2b3d3e963a`: `status: done`, `route: acp/codex-acp`. As with OpenCode, the script assertion is outside the saved run response, so API `verified` is null.

The Codex ACP sandbox was variable: the direct same-goal run (`6be8032e4960`) completed with a required command check and `verified: true`; a later script attempt failed namespace creation and its file check. After that blocked result, the permitted Codex worker-node fallback with `sandbox: workspace-write` also failed the independent check (`b8eb3f83e0fd`, `verified: false`). The final `same_goal.sh codex-acp` attempt passed. All outcomes are retained here; the sandbox behavior was not consistently reproducible.

## Earlier OpenCode observations

Before invoking the supplied script, an ad hoc OpenCode flow failed its independent command check because no file was created (`df2898b68a62`). Its single simpler retry ended with an ACP connection close (`8d6e01469f7d`). The later script-driven runs above passed; both earlier failures are included to show the observed variation.

## Command outcomes

- `setup/harnesses/verify_opencode.sh` — `OpenCode ACP verified: 1.18.35 (MIT)`
- `same_goal.sh opencode` — `opencode: PASS — hello.txt contains hi`
- `same_goal.sh codex-acp` — `codex-acp: PASS — hello.txt contains hi`
- Explicit direct Codex ACP acceptance run `6be8032e4960` — `"verified":true`
- Codex node fallback `b8eb3f83e0fd` — `"verified":false`
