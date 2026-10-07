"""Git-backed rollback helpers for run changes and saved flows."""
from __future__ import annotations

import json
import os
import re

import git


def repo():
    import vault
    return vault._repo


def _run_commits(run_id: str) -> list[git.Commit]:
    """Find only commits attributable to this exact run."""
    r = repo()
    tag = re.compile(r"\[run:" + re.escape(run_id) + r"\]", re.IGNORECASE)
    path_id = re.compile(r"(?<![A-Za-z0-9])" + re.escape(run_id) + r"(?![A-Za-z0-9])", re.IGNORECASE)
    author = f"run:{run_id}".casefold()
    out = []
    for commit in r.iter_commits():  # newest first
        message = commit.message
        if message.casefold().startswith("revert"):
            continue
        if tag.search(message) or tag.search(commit.author.name) or commit.author.name.casefold() == author:
            out.append(commit)
            continue
        if commit.author.name.casefold() == "glacier-runner" and any(
            path_id.search(path) for path in _commit_paths(commit)
        ):
            out.append(commit)
    return out


def run_commits(run_id: str) -> list[git.Commit]:
    return _run_commits(run_id)


def changes(run_id: str) -> list[dict]:
    result = []
    for commit in _run_commits(run_id):
        for path in sorted(_commit_paths(commit)):
            result.append({"path": path, "commit": commit.hexsha[:8], "author": commit.author.name})
    return result


def _commit_paths(commit: git.Commit) -> set[str]:
    if commit.parents:
        diff = commit.parents[0].diff(commit, create_patch=False)
    else:
        diff = commit.diff(git.NULL_TREE, create_patch=False)
    return {item.b_path or item.a_path for item in diff}


def undo(run_id: str) -> dict:
    import vault

    r = repo()
    with vault._lock:
        commits = _run_commits(run_id)
        if not commits:
            raise ValueError(f"No saved changes were found for run {run_id}.")

        targets = {commit.hexsha for commit in commits}
        touched = set().union(*(_commit_paths(commit) for commit in commits))
        oldest = commits[-1]
        later_commits = []
        for commit in r.iter_commits():  # newest first, up to the oldest run commit
            if commit.hexsha == oldest.hexsha:
                break
            if commit.hexsha not in targets:
                later_commits.append(commit)
        conflicts = set().union(*(
            touched & _commit_paths(commit) for commit in later_commits
        )) if later_commits else set()
        if conflicts:
            raise RuntimeError(
                "These files have later changes by someone else and were left alone: "
                + ", ".join(sorted(conflicts))
            )

        start = r.head.commit.hexsha
        try:
            for commit in commits:  # newest first; stage each inverse, then commit once
                r.git.revert(commit.hexsha, no_commit=True)
            message = f"Undo changes from run {run_id}"
            new_commit = r.index.commit(message)
        except Exception as exc:
            try:
                r.git.revert("--abort")
            except Exception:
                pass
            r.git.reset("--hard", start)
            raise RuntimeError(
                "Undo could not be completed; the vault was restored to its starting version. "
                "Files that could not be safely reverted: " + ", ".join(sorted(touched))
            ) from exc

        # Keep the rebuildable keyword and link indexes in sync with git's restored tree.
        db = vault._db()
        try:
            for path in touched:
                full_path = vault.safe_path(path)
                if os.path.isfile(full_path):
                    with open(full_path, encoding="utf-8", errors="replace") as note:
                        body = note.read()
                    db.execute("DELETE FROM fts WHERE path=?", (path,))
                    db.execute("INSERT INTO fts VALUES (?,?)", (path, body))
                    db.execute("DELETE FROM links WHERE src=?", (path,))
                    for target in re.findall(r"\[\[([^\]|#]+)", body):
                        db.execute("INSERT INTO links VALUES (?,?)", (path, target.strip()))
                else:
                    db.execute("DELETE FROM fts WHERE path=?", (path,))
                    db.execute("DELETE FROM links WHERE src=? OR dst=?", (path, path))
            db.commit()
        finally:
            db.close()
    return {"reverted": [commit.hexsha[:8] for commit in commits], "new_commit": new_commit.hexsha[:8]}


def restore_flow(env_id: str, short_commit: str) -> str:
    import app
    import runner
    import vault

    path = runner.env_path(env_id)
    vault.safe_path(path)
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", short_commit):
        raise ValueError("Enter at least 7 letters or numbers from the saved version ID.")
    matches = list(repo().iter_commits(paths=path))
    matching = [commit for commit in matches if commit.hexsha.startswith(short_commit.lower())]
    if not matching:
        raise ValueError(f"Saved version {short_commit} was not found for this flow.")
    if len(matching) > 1:
        raise ValueError("More than one saved version matches. Enter more of the version ID.")
    selected = matching[0]
    try:
        saved = selected.tree / path
    except KeyError:
        raise ValueError("That saved version does not contain this flow.")
    try:
        env = json.loads(saved.data_stream.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("That saved flow version is not valid JSON.") from exc
    result = app.save_environment(env_id, env)
    return result["commit"]
