
## W43 larger-model trial — 2026-10-07

Memory before the trial: `free -h` showed 7.6 GiB total, 4.0 GiB available, and 2.0 GiB swap (1.8 GiB free). `qwen3:1.7b` was already installed (`ollama list`: 1.4 GB); no model was pulled. `ollama show qwen3:1.7b --license` reports Apache License 2.0. The larger candidates (`qwen3:4b`, `qwen2.5-coder:3b`, and `llama3.2:3b`) were not pulled: available memory fell to 3.2 GiB after the trial, and Ollama reported the 1.7B runner using 1.7 GB with `PROCESSOR 100% GPU`. This host therefore does not match the requested 4-core CPU-only laptop. No newly pulled models require removal. `qwen2.5-coder:3b` and `llama3.2:3b` were confirmed absent with `ollama show`; no model was pulled for license inspection.

### Direct OpenCode CLI check — qwen3:1.7b

The task was exactly `Create hello.txt containing exactly: hello from glacier`. OpenCode 1.18.35 used an isolated project `opencode.json` with the local Ollama endpoint and `tool_call: true`. One setup attempt accidentally ran from the repository root rather than the project directory; it failed before using Ollama with `ProviderModelNotFoundError: Model not found: ollama/qwen3:1.7b. Did you mean: ollama-cloud?` That attempt took 1.66 seconds and peaked at 569,088 KiB RSS. It created no file. The corrected fresh attempt ran from the isolated project directory and loaded the local model:

```text
permission requested: external_directory (/home/user/*); auto-rejecting
✗ Write /home/user/hello.txt failed
Error: The user rejected permission to use this specific tool call.
exit status: 0
hello.txt: absent
```

The model requested `/home/user/hello.txt`, outside the project, so the direct check failed. Elapsed time was 59.54 seconds; OpenCode's maximum resident set was 585,852 KiB (about 572 MiB). This is OpenCode process RSS, not total system/model memory. Afterward `free -h` showed 3.4 GiB available and 1.7 GiB swap free.

The OpenCode ACP check was not run: this branch does not contain `bench/live_acp/run_live.py`, and the version on `origin/card/W28-acp-diag` is an unmerged change outside this branch. No direct-check-passing model was found in this trial, so PH2.4's live two-harness test is not met by this attempt. Existing W28 direct and ACP failures above remain the prior baseline; qwen3:1.7b has again failed the direct OpenCode tool-use check. The requested ordered model sweep and CPU-only two-harness proof remain incomplete because this host exposes a GPU runner and no larger pull met the available-memory room requirement.
