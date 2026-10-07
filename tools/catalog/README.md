# MCP capability catalog

`capabilities.yaml` is a short, reviewed shortlist of MCP servers Glacier may offer to workers. It is not an automatic installer or a trust guarantee. Before enabling a server, keep filesystem access narrow, provide only named secrets, and enforce each listed network host outside the server as well. Servers and dependencies must be reviewed again before changing their pins.

Run the catalog checker from the repository root:

```sh
/workspaces/glacier-lean/.venv/bin/python tools/catalog/check.py
```

The checker validates the required fields, OSI-approved license identifiers, exact install pins, Docker image digests, and declared permissions, then prints a summary table.

Each `source` points to the upstream repository used for review. `reviewed_by` and `reviewed_on` record provenance. Network-enabled entries list the allowed hostnames and explicitly say that Glacier's network sandbox must enforce the list; a server's own code is not treated as an egress boundary.

## Upstream source review

**Version and security review checked 2026-10-07.** The package registries reported
Filesystem `2026.8.31` and Memory `2026.8.31` via `npm view`; PyPI reported Git
`2026.8.18` and Fetch `2026.8.18` via `pip index versions`. These are the newest
published versions reported by those registries on the check date. The upstream
[modelcontextprotocol/servers security advisories](https://github.com/modelcontextprotocol/servers/security/advisories)
page was reviewed, including its Git path-validation and argument-injection advisories.
Catalog pins should be checked against the registries and advisories again before upgrades.

The following official upstream repositories document each server's purpose, install method, license, and/or release pin:

- [MCP filesystem server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem): local directory tools and configured directory access. Pin `2026.8.31`; use only approved paths.
- [MCP git server](https://github.com/modelcontextprotocol/servers/tree/main/src/git): repository inspection and modification; MIT license and PyPI package pin `2026.8.18`. Expose only approved checkouts.
- [MCP fetch server](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch): web fetching and conversion; MIT license and package pin `2026.8.18`. Upstream warns about internal/local address access, so use an egress allowlist.
- [MCP memory server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory): local knowledge-graph storage and `MEMORY_FILE_PATH` configuration; package version `2026.8.31`. This separate JSONL store does not replace Glacier's plain Markdown vault.
- [Playwright MCP](https://github.com/microsoft/playwright-mcp): browser automation; Apache-2.0 license and package pin 0.0.83. The browser is not an egress boundary, and page content may prompt-inject the worker.
- [GitHub MCP Server](https://github.com/github/github-mcp-server): GitHub repository, issue, and pull request tools; MIT license. The Docker image is pinned to the published `sha256:f1c51d1df58bebaeeb672e01c91692d87a7a6e22f44b9ca75263375b5e35b7fe` digest. Token scopes control consequential remote changes.
- [Postgres MCP](https://github.com/crystaldba/postgres-mcp): PostgreSQL inspection and queries; MIT license and package pin 0.3.0. Restricted mode is intended for read-only use; use a least-privilege database account.
- [MCP time server](https://github.com/modelcontextprotocol/servers/tree/main/src/time): time and timezone conversion; MIT license and package pin 0.6.2.
- [MCP sequential-thinking server](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking): structured, revisable reasoning; MIT license and release pin 2026.8.31. Its output still needs independent verification.

SQLite is omitted because its publisher and package scope could not be verified against its upstream repository. A calendar or email server is **to add after a maintained official repository, OSI license, and exact pin are verified**.
