from __future__ import annotations

import subprocess
from pathlib import Path

from ventures import install_all


def test_runtime_flow_binds_interpreter_without_nested_shell_quotes(tmp_path: Path) -> None:
    flow = {
        "id": "installer-acceptance-python",
        "nodes": [],
        "edges": [],
        "acceptance": [
            {
                "kind": "command",
                "cmd": '"${GLACIER_PYTHON:-$HOME/w/glacier-lean/.venv/bin/python}" -c "print(\'ok\')"',
            }
        ],
    }

    bound = install_all._runtime_flow(
        flow,
        repo_root=tmp_path,
        slug="sample",
        home=tmp_path / "home",
    )
    command = bound["acceptance"][0]["cmd"]
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
