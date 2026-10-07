"""Small ACP agent used by the acp_agent acceptance tests."""
import asyncio
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
        return NewSessionResponse(session_id="fake-session")

    async def prompt(self, session_id, prompt, **kwargs):
        text = "".join(block.text for block in prompt if isinstance(block, TextContentBlock))
        match = re.search(r"Permission path: (.+)$", text)
        path = match.group(1) if match else ""
        result = await self.connection.request_permission(
            session_id=session_id,
            tool_call=ToolCallUpdate(
                tool_call_id="fake-write",
                title="Write requested file",
                locations=[ToolCallLocation(path=path)],
            ),
            options=[PermissionOption(option_id="allow", name="Allow", kind="allow_once")],
        )
        outcome = result.outcome.outcome
        permission = "selected" if outcome == "selected" else "cancelled"
        message = f"done: {text} (permission={permission})"
        await self.connection.session_update(
            session_id=session_id,
            update=AgentMessageChunk(session_update="agent_message_chunk", content=TextContentBlock(type="text", text=message)),
        )
        return PromptResponse(stop_reason="end_turn")


if __name__ == "__main__":
    asyncio.run(acp.run_agent(FakeAgent()))
