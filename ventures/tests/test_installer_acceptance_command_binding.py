from __future__ import annotations

import os
import shutil
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
    if os.name == "nt":
        # Installed flow commands run through Git Bash on Windows, not cmd.exe.
        git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"
        bash = str(git_bash) if git_bash.is_file() else shutil.which("bash")
        assert bash, "Git Bash is required to run installed flow commands on Windows"
        result = subprocess.run([bash, "-c", command], capture_output=True, text=True, timeout=10)
    else:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
