# Tool discovery scan

`scan.py` gathers public candidates from the official MCP registry API, GitHub topics (`mcp-server`, `ai-agents`, `ollama`) and the Ollama model library. It only writes a dated Markdown proposal; it never installs or adopts a tool. A candidate needs an OSI-approved SPDX license and activity in the last 90 days. GitHub projects also need at least 50 stars. Entries already referenced in `setup/requirements.txt` or `setup/install_tools.sh` are skipped.

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
