"""MCP tools for the shared memory vault."""
import json
import os

import vault


def main() -> None:
    from mcp.server.fastmcp import FastMCP
    vault.init(os.environ.get("GLACIER_VAULT", "vault"))
    mcp = FastMCP("glacier-memory")

    @mcp.tool(name="write_note")
    def write_note(path: str, body: str, author: str = "worker:unknown", run_id: str = "") -> str:
        """Write a note as worker:<model> with the current run id."""
        if not author.startswith("worker:") or len(author) <= len("worker:"):
            raise ValueError("Worker author must start with worker:<model>")
        commit = vault.write_note(path, body, author=author, run_id=run_id)
        return f"saved {path} (commit {commit})"

    @mcp.tool(name="search")
    def search(query: str, k: int = 10) -> str:
        return json.dumps(vault.search(query, k))

    @mcp.tool(name="read_note")
    def read_note(path: str) -> str:
        return vault.read_note(path)

    @mcp.tool(name="links")
    def links(path: str) -> str:
        return json.dumps(vault.links(path))

    mcp.run()

if __name__ == "__main__":
    main()
