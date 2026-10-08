"""ACP failures should explain the subprocess failure without exposing secrets."""
import importlib.util
import os
import sys

import keyring
import secrets_store


NODE_PATH = os.path.join(os.path.dirname(__file__), "..", "nodes", "acp_agent.py")
SPEC = importlib.util.spec_from_file_location("acp_failure_details_node", NODE_PATH)
NODE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NODE)


class MemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        del self.values[(service, username)]


def _run(tmp_path, command, timeout=5):
    workdir = tmp_path / "project"
    workdir.mkdir()
    return NODE.run({
        "config": {"harness": "custom", "command": command, "workdir": str(workdir),
                   "prompt": "Say hello", "timeout": timeout},
        "env_id": "failure-details", "run_id": "fake-run", "home": str(tmp_path),
    })


def _script_command(path):
    import sys
    return f'"{sys.executable}" "{path}"'


def test_acp_reports_exit_status_and_last_stderr_lines(tmp_path):
    agent = tmp_path / "exit_agent.py"
    agent.write_text(
        "import sys\n"
        "for i in range(1, 43): print(f'error line {i}', file=sys.stderr)\n"
        "sys.exit(3)\n",
        encoding="utf-8",
    )

    result = _run(tmp_path, _script_command(agent))
    output = result["output"]

    assert result["state"] == "failed"
    assert "exit status: 3" in output.lower() or "exit code 3" in output.lower()
    stderr = output.split("Error output (last 40 lines):\n", 1)[1].splitlines()
    assert "error line 2" not in stderr
    assert "error line 3" in stderr
    assert "error line 42" in stderr


def test_acp_redacts_stored_secret_from_stderr(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    keyring.set_keyring(MemoryKeyring())
    secret = "local-agent-secret-value"
    secrets_store.set("agent-token", secret)
    agent = tmp_path / "secret_agent.py"
    agent.write_text(
        "import sys\n"
        f"print({secret!r}, file=sys.stderr)\n"
        "sys.exit(3)\n",
        encoding="utf-8",
    )

    result = _run(tmp_path, _script_command(agent))
    output = result["output"]

    assert result["state"] == "failed"
    assert secret not in output
    assert "[secret agent-token]" in output


def test_acp_timeout_has_plain_language_message(tmp_path):
    agent = tmp_path / "hanging_agent.py"
    agent.write_text(
        "import asyncio, acp\n"
        "from acp.schema import InitializeResponse, NewSessionResponse, PromptResponse\n"
        "class Agent:\n"
        " async def initialize(self, protocol_version, **kwargs): return InitializeResponse(protocol_version=protocol_version)\n"
        " async def new_session(self, cwd, **kwargs): return NewSessionResponse(session_id='hang')\n"
        " async def prompt(self, session_id, prompt, **kwargs): await asyncio.sleep(30); return PromptResponse(stop_reason='end_turn')\n"
        "asyncio.run(acp.run_agent(Agent()))\n",
        encoding="utf-8",
    )

    result = _run(tmp_path, _script_command(agent), timeout=1)

    assert result["state"] == "failed"
    assert "timed out after 1 seconds" in result["output"]


def test_acp_empty_response_is_reported_with_process_status(tmp_path):
    agent = tmp_path / "empty_agent.py"
    agent.write_text(
        "import asyncio, acp\n"
        "from acp.schema import InitializeResponse, NewSessionResponse, PromptResponse\n"
        "class Agent:\n"
        " async def initialize(self, protocol_version, **kwargs): return InitializeResponse(protocol_version=protocol_version)\n"
        " async def new_session(self, cwd, **kwargs): return NewSessionResponse(session_id='empty')\n"
        " async def prompt(self, session_id, prompt, **kwargs): return PromptResponse(stop_reason='end_turn')\n"
        "asyncio.run(acp.run_agent(Agent()))\n",
        encoding="utf-8",
    )

    result = _run(tmp_path, _script_command(agent))

    assert result["state"] == "failed"
    assert "finished without returning a message" in result["output"].lower()
    assert "process exit status: 0" in result["output"].lower()


def test_acp_successful_output_is_unchanged(tmp_path):
    fake_agent = os.path.join(os.path.dirname(__file__), "fake_acp_agent.py")
    command = _script_command(fake_agent)
    result = _run(tmp_path, command)

    assert result["state"] == "done"
    assert result["output"] == "done: Say hello (permission=cancelled)"


def test_acp_success_remains_success_when_transport_stops_agent_during_cleanup(tmp_path):
    agent = tmp_path / "lingering_agent.py"
    agent.write_text(
        "import asyncio, time, acp\n"
        "from acp.schema import AgentMessageChunk, InitializeResponse, NewSessionResponse, PromptResponse, TextContentBlock\n"
        "class Agent:\n"
        " def on_connect(self, connection): self.connection = connection\n"
        " async def initialize(self, protocol_version, **kwargs): return InitializeResponse(protocol_version=protocol_version)\n"
        " async def new_session(self, cwd, **kwargs): return NewSessionResponse(session_id='lingering')\n"
        " async def prompt(self, session_id, prompt, **kwargs):\n"
        "  await self.connection.session_update(session_id=session_id, update=AgentMessageChunk(session_update='agent_message_chunk', content=TextContentBlock(type='text', text='same successful result')))\n"
        "  return PromptResponse(stop_reason='end_turn')\n"
        "asyncio.run(acp.run_agent(Agent()))\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )

    result = _run(tmp_path, _script_command(agent))

    assert result["state"] == "done"
    assert result["output"] == "same successful result"
