# Tool discovery scan

`scan.py` gathers public candidates from the official MCP registry API, GitHub topics (`mcp-server`, `ai-agents`, `ollama`) and the Ollama model library. It only writes a dated Markdown proposal; it never installs or adopts a tool. A candidate needs an OSI-approved SPDX license and activity in the last 90 days. GitHub projects also need at least 50 stars. Entries already referenced in `setup/requirements.txt` or `setup/install_tools.sh` are skipped. Each network source has a 20 second limit and is handled separately, so an unavailable source does not stop the others.

The weekly maintenance flow calls `discover_records()` and `render_report()` to place the same filtered research leads directly in its saved maintenance note. These functions return data or Markdown without writing a file. The older standalone `scan.py` flow step remains for compatibility with the flow checks.

Run a live scan with the project Python:

```sh
/workspaces/glacier-lean/.venv/bin/python tools/scan/scan.py
```

Run against an offline JSON fixture:

```sh
/workspaces/glacier-lean/.venv/bin/python tools/scan/scan.py --offline-fixture tools/scan/example-fixture.json
```

The fixture is a JSON object keyed by the source names in `sources.yaml`. Use `{ "servers": [...] }` for `mcp`, `{ "items": [...] }` for GitHub sources and `{ "models": [...] }` for Ollama. Each record supplies `name`, `url`, `license`, and `updated_at`; GitHub records also supply `stars`. The report maps candidates to PH9.3 and requires human review before adoption.

Ollama's public library page lists model names but does not provide machine-readable OSI license or maintenance evidence. Those models are therefore not proposed unless a source payload includes that evidence; this prevents treating a model catalog listing as proof of an OSI-licensed tool.
