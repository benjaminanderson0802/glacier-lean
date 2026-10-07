"""Run a coding agent that speaks ACP over stdio.

Permission checks only protect when the agent asks permission first; this is not
an operating-system sandbox. OS sandboxing is provided by the sandboxing card.
"""
import asyncio
import os
import shlex
import shutil
from pathlib import Path

PREV_LIMIT = 8000


NODE = {
    "catalog": {
        "type": "acp_agent",
        "label": "Coding agent",
        "description": "Hands a task to an ACP coding agent such as OpenCode or Gemini CLI.",
        "worker": True,
        "fields": [
            {"key": "harness", "label": "Coding agent", "placeholder": "", "default": "opencode",
             "options": ["codex-acp", "opencode", "custom"]},
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
        root = os.path.realpath(workdir)
        resolved = os.path.realpath(target)
        if resolved == root:
            return False
        if os.path.commonpath((root, resolved)) != root:
            return False
        git_dir = os.path.join(root, ".git")
        return os.path.commonpath((os.path.realpath(git_dir), resolved)) != os.path.realpath(git_dir)
    except (OSError, ValueError):
        return False


def _permission_kind(tool_call) -> str:
    kind = getattr(tool_call, "kind", None)
    if kind:
        return str(getattr(kind, "value", kind)).lower()
    raw = getattr(tool_call, "raw_input", None)
    if isinstance(raw, dict):
        kind = raw.get("kind") or raw.get("type")
        if kind:
            return str(getattr(kind, "value", kind)).lower()
    return ""


def _permission_paths(tool_call) -> list[str]:
    """Collect path-like strings from every nested request field."""
    paths = [location.path for location in (getattr(tool_call, "locations", None) or []) if getattr(location, "path", None)]
    raw = getattr(tool_call, "raw_input", None)
    path_keys = {"path", "file", "file_path", "filepath", "target", "source", "destination", "dest",
                 "new_path", "old_path", "to", "from", "cwd", "workdir", "directory"}

    def is_path(value: str, key: str) -> bool:
        if key.lower() in path_keys:
            return True
        # Path-like strings outside named fields must also be checked, while
        # prose and shell commands are not interpreted as permission paths.
        return value.startswith(("/", "./", "../", "~")) or "/" in value or "\\" in value

    def visit(value, key=""):
        if isinstance(value, dict):
            for name, child in value.items():
                if isinstance(child, str) and is_path(child, name):
                    paths.append(child)
                else:
                    visit(child, name)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child, key)
        elif isinstance(value, str) and is_path(value, key):
            paths.append(value)

    visit(raw)
    return paths


def _acp_client(workdir: str, messages: list[str]):
    from acp.schema import AllowedOutcome, DeniedOutcome, RequestPermissionResponse

    class GlacierClient:
        async def session_update(self, session_id, update, **kwargs):
            if getattr(update, "session_update", None) == "agent_message_chunk":
                content = getattr(update, "content", None)
                text = getattr(content, "text", None)
                if text:
                    messages.append(text)

        async def request_permission(self, session_id, tool_call, options, **kwargs):
            kind = _permission_kind(tool_call)
            if kind not in {"read", "edit"}:
                return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))
            paths = _permission_paths(tool_call)
            if paths and all(_inside(path, workdir) for path in paths):
                allowed = next((option for option in options if option.kind == "allow_once"), None)
                if allowed:
                    return RequestPermissionResponse(outcome=AllowedOutcome(outcome="selected", option_id=allowed.option_id))
            return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))

    return GlacierClient()


async def _run_acp(acp, command: list[str], prompt: str, workdir: str, timeout: int) -> tuple[str, int]:
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
    try:
        import acp
    except ImportError:
        return {"state": "failed", "output": "Coding agent support is not installed", "exit_code": 1}

    config = ctx["config"]
    harness = config.get("harness") or "opencode"
    if harness == "opencode":
        command = ["opencode", "acp"]
        missing_message = "This coding agent isn't installed: opencode"
    elif harness == "codex-acp":
        command = ["codex-acp"]
        missing_message = "This coding agent isn't installed: codex-acp"
    else:
        if harness != "custom":
            return {"state": "failed", "output": f"Unknown coding agent '{harness}'. Choose codex-acp, opencode, or custom.", "exit_code": 1}
        try:
            command = shlex.split(config.get("command") or "")
        except ValueError as exc:
            return {"state": "failed", "output": f"Invalid coding agent command: {exc}", "exit_code": 1}
        if not command:
            return {"state": "failed", "output": "Enter a command for the custom coding agent", "exit_code": 1}
        missing_message = f"This coding agent isn't installed: {command[0]}"

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
        output, exit_code = asyncio.run(_run_acp(acp, command, prompt, workdir, timeout))
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
