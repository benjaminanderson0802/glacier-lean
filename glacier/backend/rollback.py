"""Git-backed rollback helpers for run changes and saved flows."""
from __future__ import annotations

import os

import git


def repo():
    import vault
    return vault._repo


def run_commits(run_id: str) -> list[git.Commit]:
    marker = f"run:{run_id}".lower()
    out = []
    for commit in repo().iter_commits():
        if marker in commit.message.lower() or marker in commit.author.name.lower() or commit.author.name.lower() == "glacier-runner" and run_id.lower() in commit.message.lower():
            out.append(commit)
    return out


def changes(run_id: str) -> list[dict]:
    result = []
    for commit in run_commits(run_id):
        for path in commit.stats.files:
            result.append({"path": path, "commit": commit.hexsha[:8], "author": commit.author.name})
    return result


def _commit_paths(commit: git.Commit) -> set[str]:
    if commit.parents:
        diff = commit.parents[0].diff(commit, create_patch=False)
    else:
        diff = commit.diff(git.NULL_TREE, create_patch=False)
    return {item.b_path or item.a_path for item in diff}


def undo(run_id: str) -> dict:
    r = repo()
    commits = run_commits(run_id)
    if not commits:
        raise ValueError(f"No saved changes were found for run {run_id}.")
    targets = {c.hexsha for c in commits}
    touched = set().union(*(_commit_paths(c) for c in commits))
    conflicts = set()
    for c in r.iter_commits():
        if c.hexsha in targets:
            break
        if c.author.name.lower() != "glacier-runner" and c.author.name.lower() != f"run:{run_id}".lower():
            conflicts.update(touched & _commit_paths(c))
    if conflicts:
        raise RuntimeError("These files have later changes by someone else and were left alone: " + ", ".join(sorted(conflicts)))

    reverted = []
    for commit in commits:  # git history iteration is newest first
        r.git.revert(commit.hexsha, no_edit=True)
        reverted.append(commit.hexsha[:8])
    return {"reverted": reverted, "new_commit": r.head.commit.hexsha[:8]}


def restore_flow(env_id: str, short_commit: str) -> str:
    import vault
    path = f"environments/{env_id}.json"
    vault.safe_path(path)
    r = repo()
    matches = list(r.iter_commits(paths=path))
    selected = next((c for c in matches if c.hexsha.startswith(short_commit)), None)
    if selected is None:
        raise ValueError(f"Saved version {short_commit} was not found for this flow.")
    try:
        body = selected.tree / path
    except KeyError:
        raise ValueError("That saved version does not contain this flow.")
    return vault.write_note(path, body.data_stream.read().decode("utf-8"), agent="owner")
