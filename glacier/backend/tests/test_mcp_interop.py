"""Real stdio interoperability checks using the official MCP Python client."""
import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


BACKEND = Path(__file__).resolve().parents[1]


async def _exercise_server(vault_path: Path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mem_server"],
        cwd=BACKEND,
        env={**os.environ, "GLACIER_VAULT": str(vault_path)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            schemas = {tool.name: tool.inputSchema for tool in tools.tools}
            saved = await session.call_tool("write_note", {
                "path": "interop/hello.md",
                "body": "MCP interoperability test note. Placeholder: ${GLACIER_TEST_SECRET}.",
                "author": "mcp:codex-test",
            })
            search = await session.call_tool("search", {"query": "interoperability"})
            read_note = await session.call_tool("read_note", {"path": "interop/hello.md"})
            listed = await session.call_tool("list_notes", {})
            history = await session.call_tool("history", {"path": "interop/hello.md"})
            note_links = await session.call_tool("links", {"path": "interop/hello.md"})
            claim = await session.call_tool("file_claim", {
                "kind": "bug", "summary": "MCP sample issue", "evidence": "Reproduced over stdio.",
                "author": "mcp:codex-test",
            })
            escaped = await session.call_tool("read_note", {"path": "../outside.md"})
            escaped_list = await session.call_tool("list_notes", {"prefix": "../"})
            malformed = await session.call_tool("write_note", {"path": "bad.txt", "body": "no"})
            bad_claim = await session.call_tool("file_claim", {
                "kind": "not-a-kind", "summary": "bad claim", "evidence": "bad input",
            })
            bad_search = await session.call_tool("search", {"query": 42})
            bad_history = await session.call_tool("history", {"path": "../outside.md"})
            bad_links = await session.call_tool("links", {"path": "../outside.md"})
            return (schemas, saved, search, read_note, listed, history, note_links, claim,
                    escaped, escaped_list, malformed, bad_claim, bad_search, bad_history, bad_links)


def test_sdk_stdio_memory_tools_are_schemas_author_safe_and_report_bad_calls(tmp_path):
    (schemas, saved, search, read_note, listed, history, note_links, claim,
     escaped, escaped_list, malformed, bad_claim, bad_search, bad_history, bad_links) = asyncio.run(
        _exercise_server(tmp_path / "vault")
    )

    assert {"search", "read_note", "write_note", "list_notes", "history", "links", "file_claim"} <= schemas.keys()
    assert schemas["write_note"]["required"] == ["path", "body"]
    assert "query" in schemas["search"]["properties"]
    assert not saved.isError
    note_path = tmp_path / "vault" / "interop" / "hello.md"
    note = note_path.read_text()
    assert "author: mcp:codex-test" in note
    assert "${GLACIER_TEST_SECRET}" in note
    assert not search.isError and "interop/hello.md" in search.content[0].text
    assert not read_note.isError and "${GLACIER_TEST_SECRET}" in read_note.content[0].text
    assert not listed.isError and "interop/hello.md" in listed.content[0].text
    assert not history.isError and "mcp:codex-test" in history.content[0].text
    assert not note_links.isError and note_links.content[0].text == "[]"
    assert not claim.isError and '"path": "claims/' in claim.content[0].text
    assert escaped.isError and "allowed" in escaped.content[0].text.lower()
    assert escaped_list.isError and "allowed" in escaped_list.content[0].text.lower()
    assert malformed.isError and "Markdown" in malformed.content[0].text
    assert bad_claim.isError and "claim type" in bad_claim.content[0].text
    assert bad_search.isError
    assert bad_history.isError and "allowed" in bad_history.content[0].text.lower()
    assert bad_links.isError and "allowed" in bad_links.content[0].text.lower()


def test_sdk_stdio_rejects_invalid_author_as_mcp_error(tmp_path):
    async def exercise():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mem_server"],
            cwd=BACKEND,
            env={**os.environ, "GLACIER_VAULT": str(tmp_path / "vault")},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool("write_note", {
                    "path": "bad.md", "body": "no", "author": "mcp:bad name",
                })

    result = asyncio.run(exercise())
    assert result.isError
    assert "author" in result.content[0].text.lower()
