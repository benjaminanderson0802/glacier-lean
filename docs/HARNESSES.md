# ACP coding agent harnesses

The ACP worker supports three harness settings:

- `opencode`: starts `opencode acp` (OpenCode CLI, MIT).
- `codex-acp`: starts `codex-acp` (the Zed Codex ACP adapter, Apache-2.0).
- `custom`: starts the command entered in the Command field.

Unknown names fail with a plain message that identifies the missing coding agent. The ACP driver grants only one-time `read` and `edit` requests for paths inside the selected work folder; it denies execute, delete, move, root-folder, and `.git` requests.

## Install and verify OpenCode

Run `setup/harnesses/install_opencode.sh` to install the pinned MIT `@opencode-ai/cli@0.0.0-beta-17823` package (whose installed CLI reports version `1.18.35`). Run `setup/harnesses/verify_opencode.sh` to check that binary version and ACP command.

OpenCode needs a configured provider/model. For an offline, no-cost option, install Ollama and pull a small instruct model below 1 GB, then copy `setup/harnesses/opencode.ollama.example.json` to `opencode.json` in the project folder. The example uses the OpenAI-compatible Ollama endpoint and `qwen3:0.6b` (522 MB in the shared sandbox). OpenCode's provider format follows its [official provider documentation](https://opencode.ai/docs/providers/). 

Install the Codex ACP adapter with `setup/harnesses/install_codex_acp.sh`. It pins the Apache-2.0 npm package `@agentclientprotocol/codex-acp@2.1.1`, which exposes the `codex-acp` command. The older `@zed-industries/codex-acp` package is deprecated. A working Codex CLI login is required; the adapter is not the proprietary CLI itself.

## Same-goal proof

`setup/harnesses/same_goal.sh` runs the same `Create hello.txt containing exactly hi` goal through both installed harnesses against a running Glacier backend (default `http://127.0.0.1:8421`; override with `GLACIER_URL`). It verifies the file contents independently after each run. The backend acceptance test uses two distinct fake ACP agents when live harness/model availability is missing.
