"""Second harness stand-in: edits the goal file and separately requests execution."""
import asyncio
import os

import acp
from acp.schema import (
    AgentMessageChunk, InitializeResponse, NewSessionResponse, PermissionOption,
    PromptResponse, TextContentBlock, ToolCallUpdate,
)


class Agent:
    def on_connect(self, connection):
        self.connection = connection
        self.cwd = None

    async def initialize(self, protocol_version, **kwargs):
        return InitializeResponse(protocol_version=protocol_version)

    async def new_session(self, cwd, **kwargs):
        self.cwd = cwd
        return NewSessionResponse(session_id="second-agent")

    async def prompt(self, session_id, prompt, **kwargs):
        target = os.path.join(self.cwd, "hello.txt")
        options = [PermissionOption(option_id="once", name="Allow once", kind="allow_once"),
                   PermissionOption(option_id="always", name="Always allow", kind="allow_always")]
        edit = await self.connection.request_permission(
            session_id=session_id,
            tool_call=ToolCallUpdate(tool_call_id="edit", title="Write hello.txt", kind="edit", raw_input={"path": target}),
            options=options,
        )
        with open(target, "w", encoding="utf-8") as output:
            output.write("hi")
        execute = await self.connection.request_permission(
            session_id=session_id,
            tool_call=ToolCallUpdate(tool_call_id="execute", title="Run a command", kind="execute", raw_input={"command": "touch escaped"}),
            options=options,
        )
        text = f"second agent wrote hello.txt (permission=once, execute={execute.outcome.outcome})"
        await self.connection.session_update(session_id=session_id,
            update=AgentMessageChunk(session_update="agent_message_chunk", content=TextContentBlock(type="text", text=text)))
        return PromptResponse(stop_reason="end_turn")


if __name__ == "__main__":
    asyncio.run(acp.run_agent(Agent()))
