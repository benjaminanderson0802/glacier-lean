"""MCP tools for the shared memory vault."""
import json
import os
import re

import vault


def _validate_worker_write(path: str, author: str, run_id: str) -> str:
    try:
        normalised = os.path.relpath(vault.safe_path(path), vault.VAULT).replace(os.sep, "/")
    except ValueError as exc:
        raise ValueError("That note path is not allowed") from exc
    if normalised == "claims" or normalised.startswith("claims/"):
        raise ValueError("Claims can't be edited from memory")
    if not normalised.endswith(".md"):
        raise ValueError("Memory notes must be Markdown files")
    if not re.fullmatch(r"worker:[A-Za-z0-9._-]{1,64}", author):
        raise ValueError("Worker author must be worker:<model> using letters, numbers, dot, underscore, or hyphen")
    if not re.fullmatch(r"[A-Za-z0-9-]{0,64}", run_id):
        raise ValueError("Run id must contain only letters, numbers, and hyphens (up to 64 characters)")
    return normalised


def main() -> None:
    from mcp.server.fastmcp import FastMCP
    vault.init(os.environ.get("GLACIER_VAULT", "vault"))
    mcp = FastMCP("glacier-memory")

    @mcp.tool(name="write_note")
    def write_note(path: str, body: str, author: str = "worker:unknown", run_id: str = "") -> str:
        """Write a note as worker:<model> with the current run id."""
        path = _validate_worker_write(path, author, run_id)
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
