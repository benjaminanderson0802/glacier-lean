"""MCP tools for the shared memory vault."""
import json
import os
import re

import vault
import claims

def _is_claims_path(path: str) -> bool:
    """Claims are never edited through memory; compare without case and with either slash (Windows/macOS ignore case)."""
    p = str(path).replace("\\", "/").casefold().lstrip("./")
    return p == "claims" or p.startswith("claims/")



def _validate_worker_write(path: str, author: str, run_id: str) -> str:
    try:
        normalised = os.path.relpath(vault.safe_path(path), vault.VAULT).replace(os.sep, "/")
    except (ValueError, OSError):
        raise ValueError("That note path is outside the memory vault or is not allowed") from None
    if _is_claims_path(normalised):
        raise ValueError("Claims can't be edited from memory")
    if not normalised.endswith(".md"):
        raise ValueError("Memory notes must be Markdown files")
    if not re.fullmatch(r"(?:worker|mcp):[A-Za-z0-9._-]{1,64}", author or ""):
        raise ValueError("Author must be worker:<model> or mcp:<client>, using letters, numbers, dot, underscore, or hyphen")
    if not re.fullmatch(r"[A-Za-z0-9-]{0,64}", run_id):
        raise ValueError("Run id must contain only letters, numbers, and hyphens (up to 64 characters)")
    return normalised


def _validate_worker_author(author: str, run_id: str) -> None:
    if not re.fullmatch(r"(?:worker|mcp):[A-Za-z0-9._-]{1,64}", author or ""):
        raise ValueError("Author must be worker:<model> or mcp:<client>, using letters, numbers, dot, underscore, or hyphen")
    if not re.fullmatch(r"[A-Za-z0-9-]{0,64}", run_id or ""):
        raise ValueError("Run id must contain only letters, numbers, and hyphens (up to 64 characters)")


def file_claim(kind: str, summary: str, evidence: str, author: str = "worker:unknown", run_id: str = "") -> str:
    """File a claim under the validated worker identity and current run."""
    _validate_worker_author(author, run_id)
    try:
        claim = claims.file_claim(kind, summary, evidence, run_id=run_id, filed_by=author)
    except ValueError as exc:
        if "kind must be one of" in str(exc):
            raise ValueError(f"Choose a claim type from: {', '.join(claims.KINDS)}") from None
        raise
    return json.dumps(claim)


def main() -> None:
    from mcp.server.fastmcp import FastMCP
    vault.init(os.environ.get("GLACIER_VAULT", "vault"))
    mcp = FastMCP("glacier-memory")

    @mcp.tool(name="write_note")
    def write_note(path: str, body: str, author: str = "mcp:unknown", run_id: str = "") -> str:
        """Create or replace a Markdown memory note, attributed to this MCP client."""
        path = _validate_worker_write(path, author, run_id)
        commit = vault.write_note(path, body, author=author, run_id=run_id)
        return f"saved {path} (commit {commit})"

    @mcp.tool(name="file_claim")
    def mcp_file_claim(kind: str, summary: str, evidence: str, author: str = "mcp:unknown", run_id: str = "") -> str:
        """File a claim labeled with this MCP client and the current run id."""
        return file_claim(kind, summary, evidence, author, run_id)

    @mcp.tool(name="search")
    def search(query: str, k: int = 10) -> str:
        """Find Markdown memory notes by keyword and return matching vault paths as JSON."""
        return json.dumps(vault.search(query, k))

    @mcp.tool(name="read_note")
    def read_note(path: str) -> str:
        """Read one Markdown memory note by its path inside the vault."""
        try:
            vault.safe_path(path)
        except (ValueError, OSError):
            raise ValueError("That note path is outside the memory vault or is not allowed") from None
        return vault.read_note(path)

    @mcp.tool(name="links")
    def links(path: str) -> str:
        """List the note paths linked from a Markdown memory note as JSON."""
        try:
            vault.safe_path(path)
        except (ValueError, OSError):
            raise ValueError("That note path is outside the memory vault or is not allowed") from None
        return json.dumps(vault.links(path))

    @mcp.tool(name="list_notes")
    def list_notes(prefix: str = "") -> str:
        """List Markdown notes in the vault, optionally under a vault-relative folder."""
        if prefix:
            try:
                full = vault.safe_path(prefix)
                prefix = os.path.relpath(full, vault.VAULT).replace(os.sep, "/")
            except (ValueError, OSError):
                raise ValueError("That folder is outside the memory vault or is not allowed") from None
        return json.dumps(vault.list_notes(".md", prefix))

    @mcp.tool(name="history")
    def history(path: str) -> str:
        """Show saved Git versions of a note, newest first, with author and message."""
        try:
            safe = os.path.relpath(vault.safe_path(path), vault.VAULT).replace(os.sep, "/")
        except (ValueError, OSError):
            raise ValueError("That note path is outside the memory vault or is not allowed") from None
        with vault._lock:
            entries = [{"commit": c.hexsha[:8], "author": c.author.name,
                        "date": c.committed_datetime.isoformat(), "message": c.message.strip()}
                       for c in vault._repo.iter_commits(paths=safe)]
        return json.dumps(entries)

    mcp.run()

if __name__ == "__main__":
    main()
