import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import vault
import runner


@pytest.mark.parametrize("resolved", [
    r"C:\Users\owner\Glacier\vault\.git\config",
    r"C:\Users\owner\Glacier\vault\.GIT\config",
    "/Users/owner/Glacier/vault/.Git/config",
])
def test_git_metadata_path_check_handles_windows_separators_and_case(resolved):
    assert vault._is_git_metadata_path(resolved)


@pytest.mark.parametrize("resolved", [
    r"C:\Users\owner\Glacier\vault\notes\plan.md",
    "/Users/owner/Glacier/vault/notes/plan.md",
])
def test_git_metadata_path_check_allows_ordinary_notes(resolved):
    assert not vault._is_git_metadata_path(resolved)


@pytest.mark.parametrize("env_id", ["../outside", r"..\..\outside", "C:\\outside"])
def test_environment_file_path_rejects_non_id_path_values(env_id):
    with pytest.raises(ValueError):
        runner.env_path(env_id)
