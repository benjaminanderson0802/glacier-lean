"""Git-backed rollback helpers for run changes and saved flows."""
from __future__ import annotations

import json
import os
import re
from contextlib import ExitStack

import git
import workspaces


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
        if tag.match(message) or tag.search(commit.author.name) or commit.author.name.casefold() == author:
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
            result.append({"path": path, "commit": commit.hexsha[:8], "author": commit.author.name, "repo": "vault"})
    for workspace, commit in _workspace_run_commits(run_id):
        for path in sorted(_commit_paths(commit)):
            result.append({"path": path, "commit": commit.hexsha[:8], "author": commit.author.name,
                           "repo": "workspace", "workspace": os.path.basename(workspace)})
    return result


def _commit_paths(commit: git.Commit) -> set[str]:
    if commit.parents:
        diff = commit.parents[0].diff(commit, create_patch=False)
    else:
        diff = commit.diff(git.NULL_TREE, create_patch=False)
    return {item.b_path or item.a_path for item in diff}


def _workspace_run_commits(run_id: str) -> list[tuple[str, git.Commit]]:
    """Find verified run merge commits in each flow's workspace repository."""
    root = os.path.join(os.path.abspath(os.environ.get("GLACIER_HOME", "data")), "workspaces")
    if not os.path.isdir(root):
        return []
    tag = re.compile(r"^\[run:" + re.escape(run_id) + r"\]", re.IGNORECASE)
    found = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        try:
            workspace_repo = git.Repo(path, search_parent_directories=False)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            continue
        for commit in workspace_repo.iter_commits():
            if tag.match(commit.message):
                found.append((path, commit))
    return found


def workspaces_lock(path: str):
    return workspaces._MergeLock(open(path, "a+"))


def _undo_conflicts(r: git.Repo, commits: list[git.Commit]) -> tuple[set[str], set[str]]:
    targets = {commit.hexsha for commit in commits}
    touched = set().union(*(_commit_paths(commit) for commit in commits))
    oldest = commits[-1]
    later_commits = []
    for commit in r.iter_commits():  # newest first, up to the oldest run commit
        if commit.hexsha == oldest.hexsha:
            break
        if commit.hexsha not in targets:
            later_commits.append(commit)
    conflicts = set().union(*(touched & _commit_paths(commit) for commit in later_commits)) if later_commits else set()
    return touched, conflicts


def _apply_undo(r: git.Repo, commits: list[git.Commit], touched: set[str], repo_name: str, run_id: str) -> dict:
    start = r.head.commit.hexsha
    try:
        for commit in commits:
            if len(commit.parents) > 1:
                r.git.revert(commit.hexsha, mainline=1, no_commit=True)
            else:
                r.git.revert(commit.hexsha, no_commit=True)
        new_commit = r.index.commit(f"Undo changes from run {run_id}")
    except Exception as exc:
        try:
            r.git.revert("--abort")
        except Exception:
            pass
        r.git.reset("--hard", start)
        raise RuntimeError(
            f"Undo could not be completed; the {repo_name} was restored to its starting version. "
            "Files that could not be safely reverted: " + ", ".join(sorted(touched))
        ) from exc
    return {"reverted": [commit.hexsha[:8] for commit in commits],
            "new_commit": new_commit.hexsha[:8], "changes": sorted(touched)}


def undo(run_id: str) -> dict:
    import vault

    r = repo()
    with vault._lock, ExitStack() as locks:
        commits = _run_commits(run_id)
        workspace_commits = _workspace_run_commits(run_id)
        if not commits and not workspace_commits:
            raise ValueError(f"No saved changes were found for run {run_id}.")

        for path in sorted({path for path, _ in workspace_commits}):
            env_id = os.path.basename(path)
            lock_path = os.path.join(os.path.dirname(path), "..", "worktrees", f"{env_id}.merge.lock")
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            locks.enter_context(workspaces_lock(lock_path))
        vault_touched, vault_conflicts = _undo_conflicts(r, commits) if commits else (set(), set())
        workspace_groups = {}
        for workspace, commit in workspace_commits:
            workspace_groups.setdefault(workspace, []).append(commit)
        workspace_plans = []
        for path, repo_commits in workspace_groups.items():
            workspace_repo = git.Repo(path)
            touched, conflicts = _undo_conflicts(workspace_repo, repo_commits)
            workspace_plans.append((path, workspace_repo, repo_commits, touched, conflicts))
        conflicts = vault_conflicts | set().union(*(plan[4] for plan in workspace_plans)) if workspace_plans else vault_conflicts
        if conflicts:
            raise RuntimeError(
                "These files have later changes by someone else and were left alone: "
                + ", ".join(sorted(conflicts))
            )

        vault_result = _apply_undo(r, commits, vault_touched, "vault", run_id) if commits else {
            "reverted": [], "new_commit": "", "changes": []
        }
        workspace_results = []
        for path, workspace_repo, repo_commits, touched, _ in workspace_plans:
            workspace_result = _apply_undo(workspace_repo, repo_commits, touched, "workspace", run_id)
            workspace_result["workspace"] = os.path.basename(path)
            workspace_results.append(workspace_result)

        # Keep the rebuildable keyword and link indexes in sync with git's restored tree.
        db = vault._db()
        try:
            for path in vault_touched:
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
    workspace_result = {
        "reverted": [short for item in workspace_results for short in item["reverted"]],
        "new_commit": workspace_results[-1]["new_commit"] if workspace_results else "",
        "changes": sorted({path for item in workspace_results for path in item["changes"]}),
        "workspaces": workspace_results,
    }
    return {"reverted": vault_result["reverted"], "new_commit": vault_result["new_commit"],
            "vault": vault_result, "workspace": workspace_result}


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
