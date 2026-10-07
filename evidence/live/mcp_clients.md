# Live MCP client interoperability

Client: Codex CLI 0.161.0 (`codex exec`), signed in with the existing ChatGPT account. The server was launched as a local stdio process using the project `.venv` and `glacier/backend/mem_server.py`. A one-run config override pointed it to `/tmp/glacier-mcp-live-W34-approved-20261007`; no persistent Codex config or project vault was changed.

Codex used the MCP server to save a note and search for its unique marker. These are the raw completed MCP call events from Codex's JSON output:

```json
{"type":"item.completed","item":{"id":"item_1","type":"mcp_tool_call","server":"glacier_memory","tool":"write_note","arguments":{"path":"live/codex-interop.md","body":"W34 live MCP interoperability marker glacier-mcp-live-20261007","author":"mcp:codex-live"},"result":{"content":[{"type":"text","text":"saved live/codex-interop.md (commit 76e5ed7f)"}],"structured_content":{"result":"saved live/codex-interop.md (commit 76e5ed7f)"}},"error":null,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"mcp_tool_call","server":"glacier_memory","tool":"search","arguments":{"query":"glacier-mcp-live-20261007"},"result":{"content":[{"type":"text","text":"[\"live/codex-interop.md\"]"}],"structured_content":{"result":"[\"live/codex-interop.md\"]"}},"error":null,"status":"completed"}}
```

The note was committed as `76e5ed7f`; the search result includes the saved path. The temporary vault is outside the repository.
