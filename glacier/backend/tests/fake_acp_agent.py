"""Small ACP agent used by the acp_agent acceptance tests."""
import asyncio
import os
import re
import sys

import acp
from acp.schema import (
    AgentMessageChunk,
    InitializeResponse,
    NewSessionResponse,
    PermissionOption,
    PromptResponse,
    RequestPermissionResponse,
    TextContentBlock,
    ToolCallLocation,
    ToolCallUpdate,
)


class FakeAgent:
    def on_connect(self, connection):
        self.connection = connection

    async def initialize(self, protocol_version, **kwargs):
        return InitializeResponse(protocol_version=protocol_version)

    async def new_session(self, cwd, **kwargs):
        self.cwd = cwd
        return NewSessionResponse(session_id="fake-session")

    async def prompt(self, session_id, prompt, **kwargs):
        text = "".join(block.text for block in prompt if isinstance(block, TextContentBlock))
        match = re.search(r"Permission request: (.*)$", text)
        request = match.group(1) if match else ""
        kind, _, value = request.partition(":")
        if not _:
            kind, value = "read", request
        locations = []
        raw_input = {}
        if kind in ("read", "edit", "delete") and value:
            locations = [ToolCallLocation(path=value)]
        elif kind == "move":
            source, _, destination = value.partition(":")
            raw_input = {"source": source, "destination": destination}
        elif kind == "execute":
            raw_input = {"command": f"sh {value}"}
        elif kind == "both":
            locations = [ToolCallLocation(path=value)]
        elif kind == "nested":
            raw_input = {"changes": [{"new_path": value}]}
        options = [PermissionOption(option_id="once", name="Allow once", kind="allow_once")]
        if kind == "both":
            options.insert(0, PermissionOption(option_id="always", name="Always allow", kind="allow_always"))
        result = await self.connection.request_permission(
            session_id=session_id,
            tool_call=ToolCallUpdate(
                tool_call_id="fake-write",
                title="Write requested file",
            kind={"shell": "execute", "none": None, "move": "move", "read": "read",
                  "edit": "edit", "delete": "delete", "both": "edit"}.get(kind, kind),
            locations=locations,
            raw_input=raw_input,
            ),
            options=options,
        )
        outcome = result.outcome.outcome
        permission = "cancelled"
        if outcome == "selected":
            permission = "once" if result.outcome.option_id == "once" else "always"
        if permission == "once" and "create hello.txt containing hi" in text:
            with open(os.path.join(self.cwd, "hello.txt"), "w", encoding="utf-8") as output:
                output.write("hi")
        message = f"done: {text} (permission={permission})"
        await self.connection.session_update(
            session_id=session_id,
            update=AgentMessageChunk(session_update="agent_message_chunk", content=TextContentBlock(type="text", text=message)),
        )
        return PromptResponse(stop_reason="end_turn")


if __name__ == "__main__":
    asyncio.run(acp.run_agent(FakeAgent()))
