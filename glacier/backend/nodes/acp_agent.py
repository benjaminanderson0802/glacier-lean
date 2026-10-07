"""Run a coding agent that speaks the Agent Client Protocol over stdio."""
import asyncio
import os
import shlex
import shutil
from pathlib import Path

import acp
from acp.schema import AllowedOutcome, DeniedOutcome, RequestPermissionResponse


PREV_LIMIT = 8000


NODE = {
    "catalog": {
        "type": "acp_agent",
        "label": "Coding agent",
        "description": "Hands a task to an ACP coding agent such as OpenCode or Gemini CLI.",
        "worker": True,
        "fields": [
            {"key": "harness", "label": "Coding agent", "placeholder": "", "default": "opencode",
             "options": ["opencode", "gemini", "custom"]},
            {"key": "command", "label": "Command", "placeholder": "python fake_acp_agent.py", "default": "", "optional": True},
            {"key": "prompt", "label": "Task ({env} {run} {prev_output})", "placeholder": "Fix the failing tests: {prev_output}", "default": "", "multiline": True},
            {"key": "workdir", "label": "Working folder", "placeholder": "default: GLACIER_HOME/workspaces/<env>", "default": "", "optional": True},
            {"key": "timeout", "label": "Time limit (seconds)", "placeholder": "1800", "default": 1800, "optional": True},
        ],
        "branches": None,
    },
    "run": None,
}


def _inside(path_value: str, workdir: str) -> bool:
    try:
        target = Path(path_value).expanduser()
        if not target.is_absolute():
            target = Path(workdir) / target
        return os.path.commonpath((os.path.realpath(workdir), os.path.realpath(target))) == os.path.realpath(workdir)
    except (OSError, ValueError):
        return False


def _permission_paths(tool_call) -> list[str]:
    """Get explicit affected paths from the standard ACP locations or raw input."""
    paths = [location.path for location in (getattr(tool_call, "locations", None) or []) if getattr(location, "path", None)]
    raw = getattr(tool_call, "raw_input", None)

    def visit(value, key=""):
        if isinstance(value, dict):
            for name, child in value.items():
                if name.lower() in {"path", "file", "file_path", "filepath", "target"} and isinstance(child, str):
                    paths.append(child)
                else:
                    visit(child, name)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child, key)

    visit(raw)
    return paths


def _acp_client(workdir: str, messages: list[str]):
    class GlacierClient:
        async def session_update(self, session_id, update, **kwargs):
            if getattr(update, "session_update", None) == "agent_message_chunk":
                content = getattr(update, "content", None)
                text = getattr(content, "text", None)
                if text:
                    messages.append(text)

        async def request_permission(self, session_id, tool_call, options, **kwargs):
            paths = _permission_paths(tool_call)
            if paths and all(_inside(path, workdir) for path in paths):
                allowed = next((option for option in options if option.kind in ("allow_once", "allow_always")), None)
                if allowed:
                    return RequestPermissionResponse(outcome=AllowedOutcome(outcome="selected", option_id=allowed.option_id))
            return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))

    return GlacierClient()


async def _run_acp(command: list[str], prompt: str, workdir: str, timeout: int) -> tuple[str, int]:
    messages: list[str] = []
    client = _acp_client(workdir, messages)
    async with acp.spawn_agent_process(client, command[0], *command[1:], cwd=workdir) as (connection, process):
        await connection.initialize(protocol_version=acp.PROTOCOL_VERSION)
        session = await connection.new_session(cwd=workdir)
        try:
            await asyncio.wait_for(
                connection.prompt(session_id=session.session_id, prompt=[acp.text_block(prompt)]),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return f"Coding agent timed out after {timeout} seconds", 1
        if process.returncode not in (None, 0):
            return "\n".join(messages) or f"Coding agent exited with code {process.returncode}", 1
    return "".join(messages), 0


def run(ctx):
    config = ctx["config"]
    harness = config.get("harness") or "opencode"
    if harness not in ("opencode", "gemini", "custom"):
        return {"state": "failed", "output": f"Unknown coding agent harness: {harness}", "exit_code": 1}

    if harness == "opencode":
        command = ["opencode", "acp"]
        missing_message = "OpenCode is not installed"
    elif harness == "gemini":
        command = ["gemini", "--experimental-acp"]
        missing_message = "Gemini CLI is not installed"
    else:
        try:
            command = shlex.split(config.get("command") or "")
        except ValueError as exc:
            return {"state": "failed", "output": f"Invalid coding agent command: {exc}", "exit_code": 1}
        if not command:
            return {"state": "failed", "output": "Enter a command for the custom coding agent", "exit_code": 1}
        missing_message = f"Coding agent command is not installed: {command[0]}"

    if shutil.which(command[0]) is None:
        return {"state": "failed", "output": missing_message, "exit_code": 1}

    prompt = config.get("prompt") or ""
    prompt = prompt.replace("{env}", str(ctx["env_id"])).replace("{run}", str(ctx["run_id"]))
    previous = str((ctx.get("prev") or {}).get("output", ""))[-PREV_LIMIT:]
    prompt = prompt.replace("{prev_output}", previous)
    if not prompt.strip():
        return {"state": "failed", "output": "Enter a task for the coding agent", "exit_code": 1}

    home = os.path.abspath(ctx.get("home") or os.environ.get("GLACIER_HOME", "data"))
    workdir = os.path.abspath(config.get("workdir") or os.path.join(home, "workspaces", str(ctx["env_id"])))
    os.makedirs(workdir, exist_ok=True)
    try:
        timeout = max(1, int(config.get("timeout") or 1800))
    except (TypeError, ValueError):
        timeout = 1800

    try:
        output, exit_code = asyncio.run(_run_acp(command, prompt, workdir, timeout))
    except FileNotFoundError:
        return {"state": "failed", "output": missing_message, "exit_code": 1}
    except Exception as exc:
        return {"state": "failed", "output": f"Coding agent could not complete the task: {exc}", "exit_code": 1}

    if not output:
        output = "The coding agent finished without a message"
    return {
        "state": "done" if exit_code == 0 else "failed",
        "output": output,
        "exit_code": exit_code,
        "usage": {"model": harness, "route": f"acp/{harness}", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0},
    }


NODE["run"] = run
