"""A vault reached through another spelling of its folder still saves and lists notes.

On Windows the same folder can be C:\\Users\\RUNNER~1\\... (8.3 short name) and
C:\\Users\\runneradmin\\...; note paths are resolved, so the vault root must be too.
A symlinked folder is the Linux equivalent of that second spelling.
"""
import os
import ntpath

import pytest

import vault


def test_vault_opened_through_an_alias_saves_and_lists_notes(tmp_path):
    real = tmp_path / "real-home"
    real.mkdir()
    alias = tmp_path / "alias-home"
    try:
        os.symlink(real, alias, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"this system refused to create a test symlink: {exc}")
    vault.init(str(alias / "vault"))
    vault.write_note("notes/decision.md", "# Decision\n\nKeep it lean.", agent="test")
    assert "notes/decision.md" in vault.list_notes()
    assert "Keep it lean." in vault.read_note("notes/decision.md")
    assert vault.VAULT == os.path.realpath(str(real / "vault"))


@pytest.mark.parametrize("root,full", [
    (r"C:\Users\Runner\vault", r"C:\Users\Runner\vault\claims\claim.md"),
    (r"C:\Users\Runner\vault", r"\\?\C:\Users\Runner\vault\claims\claim.md"),
])
def test_windows_path_comparison_accepts_resolved_drive_spellings(root, full):
    """Windows commonpath semantics handle drive letters and extended prefixes."""
    resolved = vault._plain(full)
    assert vault._is_within_vault(resolved, root, ntpath)


def test_windows_path_comparison_accepts_eight_dot_three_root_alias():
    short_root = r"C:\Users\RUNNER~1\AppData\Local\Temp\vault"
    long_full = r"C:\Users\runneradmin\AppData\Local\Temp\vault\claims\claim.md"
    resolved_root = r"C:\Users\runneradmin\AppData\Local\Temp\vault"
    assert vault._is_within_vault(long_full, resolved_root, ntpath)
    assert not vault._is_within_vault(long_full, short_root, ntpath)


def test_windows_relative_backslash_path_normalizes_for_join():
    relative = r"claims\claim.md".replace("\\", "/")
    assert ntpath.normcase(ntpath.join(r"C:\Users\Runner\vault", relative)) == ntpath.normcase(
        r"C:\Users\Runner\vault\claims\claim.md"
    )


def test_path_containment_accepts_children_and_rejects_sibling_prefixes():
    root = "/tmp/vault"
    assert vault._is_within_vault("/tmp/vault/claims/claim.md", root)
    assert not vault._is_within_vault("/tmp/vault-backup/claim.md", root)
    assert vault._is_within_vault(r"C:\Users\runneradmin\vault\claims\claim.md",
                                  r"C:\Users\runneradmin\vault", ntpath)
