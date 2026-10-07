# MCP capability catalog

`check.py` checks the catalog's required fields, OSI-approved license identifiers, immutable version pins, and declared permissions. It prints a compact summary when the catalog passes.

Run it from the repository root:

```sh
/workspaces/glacier-lean/.venv/bin/python tools/catalog/check.py
```

The catalog is a reviewed shortlist, not an automatic installer or a trust guarantee. Before enabling a server, keep filesystem access narrow, provide only named secrets, and enforce each listed network host outside the server as well. Servers and dependencies must be reviewed again before changing their pins.

Each `source` points to the upstream repository used for review. `reviewed_by` and `reviewed_on` record the review provenance. Risk notes call out relevant effects such as remote access, prompt injection from web pages, browser control, or irreversible external writes.

The checker requires permission maps with exactly these keys:

- `files`: filesystem paths and access levels, such as `workspace:read`.
- `network_access`: whether the server can make outbound network requests.
- `network_hosts`: allowed destination hostnames; must be non-empty when network access is enabled.
- `secrets`: secret names the server may receive; never secret values.

## Upstream source review

The source repositories, licenses, release pins, and install instructions were checked on 2026-10-07. Each catalog row links to its upstream repository; these official upstream pages document the server's purpose, setup, or license. Pins are deliberately exact and must be reviewed again before changing.

- [MCP filesystem server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem): local directory access and package release details; only configured directories should be exposed.
- [MCP git server](https://github.com/modelcontextprotocol/servers/tree/main/src/git): local repository operations, install guidance, and MIT license. Git tools can change content, so only approved checkouts should be exposed.
- [MCP fetch server](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch): web fetching and conversion; its project metadata declares MIT and its README warns about access to local/internal addresses.
- [MCP memory server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory): local knowledge graph storage. This is separate from Glacier's plain-file vault contract and must not become the only copy of user memory.
- [Playwright MCP](https://github.com/microsoft/playwright-mcp): browser automation; the official package metadata lists Apache-2.0 and its README warns that the server is not a security boundary.
- [GitHub MCP Server](https://github.com/github/github-mcp-server): GitHub repository, issue, and pull request tools; upstream repository declares MIT and documents token-based access.
- [Database MCP SQLite server](https://github.com/arifulislamat/database-mcp): SQLite queries; its published package documents MIT, read-only defaults, row caps, and query timeouts.
- [Postgres MCP](https://github.com/crystaldba/postgres-mcp): PostgreSQL inspection and queries; upstream project metadata declares MIT, with restricted access mode for read-only use.

The SQLite, Postgres, and GitHub servers can expose or change important project data. Keep read-only access as the default, provide only the specific files or database credentials each worker needs, and use approval gates before writes.
