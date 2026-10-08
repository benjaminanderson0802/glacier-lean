# Portable backend swap bench

`run_portable.py` starts an isolated Glacier backend and saves the same one-worker flow for Codex CLI and local Ollama models through OpenCode ACP (defaults to installed `qwen2.5-coder:7b`; override with `GLACIER_PORTABLE_LOCAL_MODEL`). It first attempts a tiny Python function with tests. The independent acceptance check runs `python -m pytest -q` in the workspace after each run. If one backend cannot complete it, the bench also runs the same simpler function-plus-test goal across all configured backends and reports both attempts. Each run may take up to 30 minutes for slow local inference.

The run records elapsed time, Glacier verification, the independent result, route, raw worker output and a normalized flow comparison. Flow snapshots normalize per-run identifiers and workspace paths, and remove only the backend selector details. The coding flow snapshot must otherwise be identical.

Run from the repository root with the project interpreter:

```sh
.venv/bin/python bench/portable/run_portable.py
```

Prerequisites are Codex CLI already signed in, OpenCode with Ollama configured as below, Ollama running with the selected model already installed (default `qwen2.5-coder:7b`; no model downloads), and the repository `.venv` dependencies. The runner does not print or save credentials.

OpenCode ACP uses a project `opencode.json` with the Ollama provider configured in the temporary project. The runner creates this file only in the temporary workspace. Every configured Ollama model is a local backend through the same open-source harness; these model runs are separate model routes, not separate harnesses.
