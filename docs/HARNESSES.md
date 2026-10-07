# ACP coding agent harnesses

The ACP worker supports three harness settings:

- `opencode`: starts `opencode acp` (OpenCode CLI, MIT).
- `codex-acp`: starts `codex-acp` (the official ACP Codex adapter, Apache-2.0).
- `custom`: starts the command entered in the Command field.

When no harness is selected, OpenCode is used. Unknown names fail with `Unknown coding agent '<name>'. Choose codex-acp, opencode, or custom.` A known preset whose command is missing reports `This coding agent isn't installed: <name>`. The ACP driver grants only one-time `read` and `edit` requests for paths inside the selected work folder; it denies execute, delete, move, root-folder, and `.git` requests.

## Install and verify OpenCode

Run `setup/harnesses/install_opencode.sh` to install the pinned MIT `opencode-ai@1.18.35` package. Run `setup/harnesses/verify_opencode.sh` to check that binary version and ACP command. The package name, version, and license were checked with `npm view opencode-ai name version repository.url license`; see the [official OpenCode install docs](https://opencode.ai/docs/#install) and [OpenCode repository](https://github.com/anomalyco/opencode).

OpenCode needs a configured provider/model. For an offline, no-cost option, install Ollama and pull a small instruct model below 1 GB, then copy `setup/harnesses/opencode.ollama.example.json` to `opencode.json` in the project folder. The example uses the OpenAI-compatible Ollama endpoint and `qwen3:0.6b`. OpenCode's provider format follows its [official provider documentation](https://opencode.ai/docs/providers/).

Install the Codex ACP adapter with `setup/harnesses/install_codex_acp.sh`. It pins the Apache-2.0 npm package `@agentclientprotocol/codex-acp@2.1.1`, which exposes the `codex-acp` command. Package metadata was checked with `npm view @agentclientprotocol/codex-acp name version repository.url license`; see the [adapter's official installation instructions](https://github.com/agentclientprotocol/codex-acp#installation). A working Codex CLI login is required; the adapter is not the proprietary CLI itself.

## Same-goal proof

`setup/harnesses/same_goal.sh` runs the same `Create hello.txt containing exactly hi` goal through both installed harnesses against a running Glacier backend (default `http://127.0.0.1:8421`; override with `GLACIER_URL`). It verifies the file contents independently after each run. The Python executable defaults to `python3`; override it with `GLACIER_PYTHON`.

### Live results — 2026-10-07

- [Local AI run](../evidence/live/local_ai.md): real `qwen3:0.6b` through Ollama returned the requested token offline (no cloud model used); its independent rubric check failed, so the run is recorded as unverified.
- [Same-goal harness runs](../evidence/live/same_goal.md): the supplied script passed its independent `hello.txt == hi` check for both OpenCode and Codex ACP on the final runs. Codex ACP sandbox namespace failures and a failed Codex worker-node fallback were also observed; the results file records the variation. The script checks are separate from the backend run API, so those script-driven runs have no saved `verified` field.

The backend acceptance tests still exercise two different fake ACP agents: one asks for a straightforward edit, and the other asks for an edit and a forbidden execute request. These live results supplement those tests and do not change their scope.

## Live proof

`bench/live_acp/run_live.py` starts its own real Glacier backend with temporary state, creates one ACP worker flow for OpenCode and another for Codex ACP, and asks each to create `hello.txt` containing exactly `hello from glacier`. Glacier runs the independent command check `test "$(cat hello.txt)" = "hello from glacier"`; the script repeats that check against the actual workspace. It records both backend and independent results, elapsed time, route, token counts, cost, and raw step output in [the live proof](../evidence/live/acp_two_harnesses.md). Output is scrubbed for the temporary Glacier install token and common token formats. The detailed prerequisites, user-only installation command, and reproduction steps are in [bench/live_acp/README.md](../bench/live_acp/README.md). `--dry-run` checks the proof inputs without installing or starting a harness.

The proof pins OpenCode 1.18.35 (MIT) and `@agentclientprotocol/codex-acp` 2.1.1 (Apache-2.0). OpenCode uses `qwen3:1.7b` from the local Ollama service. Codex ACP uses the existing official Codex CLI login and the current Codex config (`gpt-6-luna`, low effort); the proof script does not read or copy the login credential.
