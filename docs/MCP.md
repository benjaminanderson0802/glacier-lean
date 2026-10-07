# Connect an MCP client to Glacier memory

Glacier exposes its local Markdown vault as an MCP stdio server. Start it from a client that supports MCP, then use the `glacier-memory` server in that client. The server runs as a child process; it does not open a network port.

## Repository checkout

Replace `/absolute/path/to/repo` with this checkout's full path. In this repository the Python environment is `.venv` at the repository root, while the server module is in `glacier/backend/`.

For Claude Desktop, add this under `mcpServers` in its `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "glacier-memory": {
      "command": "/absolute/path/to/repo/.venv/bin/python",
      "args": ["/absolute/path/to/repo/glacier/backend/mem_server.py"],
      "env": {"GLACIER_VAULT": "/absolute/path/to/repo/vault"}
    }
  }
}
```

On Windows, use `C:\\absolute\\path\\to\\repo\\.venv\\Scripts\\python.exe` and `C:\\absolute\\path\\to\\repo\\glacier\\backend\\mem_server.py`. Set the vault to a local folder you control.

For Codex, add this to `~/.codex/config.toml`:

```toml
[mcp_servers.glacier-memory]
command = "/absolute/path/to/repo/.venv/bin/python"
args = ["/absolute/path/to/repo/glacier/backend/mem_server.py"]
env = { GLACIER_VAULT = "/absolute/path/to/repo/vault" }
```

For OpenCode, add this to `opencode.json` in your project or OpenCode configuration directory:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "glacier-memory": {
      "type": "local",
      "command": [
        "/absolute/path/to/repo/.venv/bin/python",
        "/absolute/path/to/repo/glacier/backend/mem_server.py"
      ],
      "environment": {"GLACIER_VAULT": "/absolute/path/to/repo/vault"},
      "enabled": true
    }
  }
}
```

## Installed desktop app

The packaged app keeps `backend/` beside `runtime/`. Point the client at the bundled interpreter and server script. Use absolute paths to the installed app resources, not a relative path from the client configuration file.

The packaged runtime is inside a platform folder under `runtime/`. Use the matching absolute path:

```text
Linux:   /absolute/path/to/app/runtime/x86_64-unknown-linux-gnu/bin/python3.12
macOS:   /absolute/path/to/app/runtime/aarch64-apple-darwin/bin/python3.12
Windows: C:\\absolute\\path\\to\\app\\runtime\\x86_64-pc-windows-msvc\\python.exe
```

For any client, pass the matching runtime command above and this server argument:

```text
/absolute/path/to/app/backend/mem_server.py
```

For example, the Claude Desktop server entry on Linux or macOS is:

```json
"glacier-memory": {
  "command": "/absolute/path/to/app/runtime/x86_64-unknown-linux-gnu/bin/python3.12",
  "args": ["/absolute/path/to/app/backend/mem_server.py"],
  "env": {"GLACIER_VAULT": "/absolute/path/to/user-local-app-data/org.glacier.desktop/vault"}
}
```

The matching Codex entry is:

```toml
[mcp_servers.glacier-memory]
command = "/absolute/path/to/app/runtime/x86_64-unknown-linux-gnu/bin/python3.12"
args = ["/absolute/path/to/app/backend/mem_server.py"]
env = { GLACIER_VAULT = "/absolute/path/to/user-local-app-data/org.glacier.desktop/vault" }
```

The matching OpenCode entry is:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "glacier-memory": {
      "type": "local",
      "command": [
        "/absolute/path/to/app/runtime/x86_64-unknown-linux-gnu/bin/python3.12",
        "/absolute/path/to/app/backend/mem_server.py"
      ],
      "environment": {"GLACIER_VAULT": "/absolute/path/to/user-local-app-data/org.glacier.desktop/vault"},
      "enabled": true
    }
  }
}
```

Replace the runtime platform folder and vault path for the computer. Glacier stores its desktop data in the user's local app data directory (`org.glacier.desktop`); set `GLACIER_VAULT` to that directory's `vault` subfolder. On macOS use `runtime/aarch64-apple-darwin/bin/python3.12`; on Windows use `runtime\\x86_64-pc-windows-msvc\\python.exe` and `backend\\mem_server.py`. Keep the writable vault in user-local data even if the app itself is installed in a protected folder.

## Tools

| Tool | What it does |
| --- | --- |
| `search(query, k=10)` | Finds notes by keyword and returns matching vault paths. |
| `read_note(path)` | Reads one Markdown note. |
| `write_note(path, body, author="mcp:unknown", run_id="")` | Creates or replaces a Markdown note and saves a Git history entry. Use an author such as `mcp:claude-desktop`. |
| `list_notes(prefix="")` | Lists Markdown notes, optionally under a vault folder. |
| `history(path)` | Lists saved versions newest first, with commit, author, date, and message. |
| `links(path)` | Lists note links from the selected note. |
| `file_claim(kind, summary, evidence, author="worker:unknown", run_id="")` | Records a claim in the claims folder using Glacier's claim format. |

## Safety

- The server can read or write only inside the configured vault. Write paths must end in `.md`; claims cannot be changed with `write_note`. Traversal and outside-vault paths are refused with a plain error.
- Notes are written through Glacier's vault writer, committed to Git, and labeled with the supplied `mcp:<client>` author. Use a short client name with letters, numbers, `.`, `_`, or `-`.
- Values that look like secret placeholders are stored as literal text. The memory server does not resolve secrets or read the operating system keychain.
- Treat note contents as untrusted text. A note cannot grant tools, change this server's permissions, or authorize an external action.
- The server communicates over the local process's stdin and stdout. Keep protocol output on stdout; diagnostics belong on stderr. No engine token is used because the server is not an HTTP API.
- Give each client only the vault it should be able to read and edit. A client with this server can create and replace notes in that vault.
