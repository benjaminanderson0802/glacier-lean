from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ventures import install_all


def _sample_flow() -> dict:
    return {
        "id": "windows-path-proof",
        "nodes": [
            {
                "id": "run",
                "type": "command",
                "config": {"cmd": "python -c \"print('ok')\"", "cwd": "{repo}"},
            }
        ],
        "edges": [],
    }


def test_runtime_flow_binds_windows_python_path_without_regex_replacement_errors(tmp_path: Path) -> None:
    windows_python = r"C:\Users\Benja\glacier-dev\.venv\Scripts\python.exe"
    with patch.object(install_all.sys, "executable", windows_python), patch.object(
        install_all.os, "pathsep", ";"
    ):
        flow = install_all._runtime_flow(
            _sample_flow(), repo_root=Path(r"C:\Users\Benja\glacier-dev"),
            slug="sample", home=tmp_path,
        )

    command = flow["nodes"][0]["config"]["cmd"]
    assert "'C:/Users/Benja/glacier-dev/.venv/Scripts/python.exe'" in command
    assert "C:/Users/Benja/glacier-dev" in command


def test_runtime_flow_uses_windows_pythonpath_separator_and_no_posix_path_append(tmp_path: Path) -> None:
    windows_python = r"C:\Users\Benja\glacier-dev\.venv\Scripts\python.exe"
    with patch.object(install_all.sys, "executable", windows_python), patch.object(
        install_all.os, "pathsep", ";"
    ):
        flow = install_all._runtime_flow(
            _sample_flow(), repo_root=Path(r"C:\Users\Benja\glacier-dev"),
            slug="sample", home=tmp_path,
        )

    command = flow["nodes"][0]["config"]["cmd"]
    assert "C:/Users/Benja/glacier-dev;C:/Users/Benja/glacier-dev/ventures/sample" in command
    assert "${PYTHONPATH:+:$PYTHONPATH}" not in command


def test_runtime_flow_quotes_a_windows_interpreter_path_with_spaces(tmp_path: Path) -> None:
    windows_python = r"C:\Program Files\Glacier Python\python.exe"
    with patch.object(install_all.sys, "executable", windows_python), patch.object(
        install_all.os, "pathsep", ";"
    ):
        flow = install_all._runtime_flow(
            _sample_flow(), repo_root=Path(r"C:\Users\Benja\glacier-dev"),
            slug="sample", home=tmp_path,
        )

    command = flow["nodes"][0]["config"]["cmd"]
    assert "'C:/Program Files/Glacier Python/python.exe'" in command
