"""Test: shared memory vault through MCP - save notes (one git commit each), keyword search, wiki links, event log, undo with git."""
import asyncio, json, os, shutil, sqlite3, sys
import git
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

NOTES = [
    ("projects/glacier.md", "# Glacier\nDesktop AI orchestrator. Uses [[decisions/engine]] and [[agents/builder]]."),
    ("decisions/engine.md", "# Engine\nWorkflows run on Microsoft Agent Framework with DBOS schedules."),
    ("agents/builder.md", "# Builder\nWrites code in its own git worktree. Never merges without passing tests."),
]

async def main():
    params = StdioServerParameters(command=sys.executable, args=["mem_server.py"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            assert tools == ["links", "read_note", "search", "write_note"], tools
            for p, b in NOTES:
                await s.call_tool("write_note", {"path": p, "body": b, "agent": "test"})
            hits = json.loads((await s.call_tool("search", {"query": "which framework runs workflows"})).content[0].text)
            assert hits and hits[0] == "decisions/engine.md", hits
            lk = json.loads((await s.call_tool("links", {"path": "projects/glacier.md"})).content[0].text)
            assert sorted(lk) == ["agents/builder", "decisions/engine"], lk
    repo = git.Repo("vault")
    commits = list(repo.iter_commits())
    assert len(commits) == 3, len(commits)
    events = sqlite3.connect("vault/.index.sqlite").execute("SELECT count(*) FROM events").fetchone()[0]
    assert events == 3, events
    repo.git.revert("HEAD", no_edit=True)
    assert not os.path.exists("vault/agents/builder.md"), "undo failed"
    print("PASS memory: 3 notes = 3 git commits, keyword search found the right note, links parsed, event log has 3 entries, git revert undid the last note")

if __name__ == "__main__":
    shutil.rmtree("vault", ignore_errors=True)
    asyncio.run(main())
