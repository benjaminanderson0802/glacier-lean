"""Second harness stand-in: edits the goal file and separately requests execution."""
import asyncio
import os
import re

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
        prompt_text = "".join(getattr(block, "text", "") for block in prompt)
        permission_target = re.search(r"Permission request: (.*)$", prompt_text)
        requested_path = permission_target.group(1) if permission_target else target
        options = [PermissionOption(option_id="once", name="Allow once", kind="allow_once"),
                   PermissionOption(option_id="always", name="Always allow", kind="allow_always")]
        edit = await self.connection.request_permission(
            session_id=session_id,
            tool_call=ToolCallUpdate(tool_call_id="edit", title="Write hello.txt", kind="edit", raw_input={"path": requested_path}),
            options=options,
        )
        selected_once = edit.outcome.outcome == "selected" and edit.outcome.option_id == "once"
        if selected_once:
            with open(target, "w", encoding="utf-8") as output:
                output.write("hi")
        execute = await self.connection.request_permission(
            session_id=session_id,
            tool_call=ToolCallUpdate(tool_call_id="execute", title="Run a command", kind="execute", raw_input={"command": "touch escaped"}),
            options=options,
        )
        edit_outcome = edit.outcome.outcome
        edit_choice = getattr(edit.outcome, "option_id", "") if edit_outcome == "selected" else ""
        text = f"second agent edit={edit_outcome}:{edit_choice}, execute={execute.outcome.outcome}"
        await self.connection.session_update(session_id=session_id,
            update=AgentMessageChunk(session_update="agent_message_chunk", content=TextContentBlock(type="text", text=text)))
        return PromptResponse(stop_reason="end_turn")


if __name__ == "__main__":
    asyncio.run(acp.run_agent(Agent()))
