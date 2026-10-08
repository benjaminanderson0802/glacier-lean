"""Git-backed rollback helpers for run changes and saved flows."""
from __future__ import annotations

import json
import os
import re
from contextlib import ExitStack

import git
import workspaces


def repo():
    """Return the shared vault Repo; callers must hold vault._lock for Git access."""
    import vault
    return vault._repo


def _run_commits(run_id: str) -> list[git.Commit]:
    """Find commits for this run; caller must hold vault._lock."""
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
    import vault
    with vault._lock:
        return _run_commits(run_id)


def _vault_change_log() -> list[tuple[str, str, str, set[str]]]:
    """(sha, author, subject, changed paths) for every vault commit, newest first.

    One separate `git log` process: no shared repository object, so no vault lock,
    and note saves never wait while a long history is scanned.
    """
    import vault
    output = git.Git(vault.VAULT).log("--format=%x1e%H%x1f%an%x1f%s", "--name-only", "-M", "--root")
    entries = []
    for record in output.split("\x1e"):
        if not record.strip():
            continue
        header, _, names = record.partition("\n")
        sha, author, subject = (header.split("\x1f", 2) + ["", ""])[:3]
        entries.append((sha, author, subject, {line.strip() for line in names.splitlines() if line.strip()}))
    return entries


def changes(run_id: str) -> list[dict]:
    result = []
    # Same matching rules as _run_commits, read from one git log instead of per-commit diffs.
    tag = re.compile(r"\[run:" + re.escape(run_id) + r"\]", re.IGNORECASE)
    path_id = re.compile(r"(?<![A-Za-z0-9])" + re.escape(run_id) + r"(?![A-Za-z0-9])", re.IGNORECASE)
    author_name = f"run:{run_id}".casefold()
    for sha, author, subject, paths in _vault_change_log():
        if subject.casefold().startswith("revert"):
            continue
        matched = tag.match(subject) or tag.search(author) or author.casefold() == author_name or (
            author.casefold() == "glacier-runner" and any(path_id.search(path) for path in paths))
        if matched:
            for path in sorted(paths):
                result.append({"path": path, "commit": sha[:8], "author": author, "repo": "vault"})
    # Workspace repositories are independent and opened/closed per operation.
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
        # --grep is anchored so similarly named runs cannot claim one another's commits.
        try:
            for commit in workspace_repo.iter_commits(grep=f"^\\[run:{re.escape(run_id)}\\]"):
                if tag.match(commit.message):
                    found.append((path, commit))
        finally:
            workspace_repo.close()
    return found


def workspaces_lock(path: str):
    return workspaces._MergeLock(open(path, "a+"))


def _undo_conflicts(r: git.Repo, commits: list[git.Commit]) -> tuple[set[str], set[str]]:
    """Inspect vault history; caller must hold vault._lock."""
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


def _repo_status(r: git.Repo) -> str:
    return r.git.status("--porcelain")


def _dirty_paths(r: git.Repo) -> set[str]:
    return {line[3:] for line in _repo_status(r).splitlines() if len(line) > 3}


def _rollback_repo(r: git.Repo, start: str):
    """Restore git state after a failed multi-repository undo."""
    try:
        r.git.revert("--abort")
    except Exception:
        pass
    r.git.reset("--hard", start)


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
    """Undo changes while holding vault lock before sorted workspace merge locks."""
    import vault

    r = repo()
    workspace_commits = _workspace_run_commits(run_id)
    workspace_groups = {}
    for workspace, commit in workspace_commits:
        workspace_groups.setdefault(workspace, []).append(commit)
    workspace_plans = []
    workspace_results = []
    vault_result = {"reverted": [], "new_commit": "", "changes": []}

    # Global lock order: vault._lock first, then workspace merge locks in sorted
    # path order. Workspace merge code never acquires vault._lock while holding
    # a merge lock, so rollback cannot form a lock cycle.
    with vault._lock, ExitStack() as locks:
        try:
            for path in sorted(workspace_groups):
                env_id = os.path.basename(path)
                lock_path = os.path.join(os.path.dirname(path), "..", "worktrees", f"{env_id}.merge.lock")
                os.makedirs(os.path.dirname(lock_path), exist_ok=True)
                locks.enter_context(workspaces_lock(lock_path))

            for path, repo_commits in sorted(workspace_groups.items()):
                workspace_repo = git.Repo(path)
                try:
                    if _repo_status(workspace_repo):
                        raise RuntimeError("main has uncommitted changes; undo skipped so nothing is overwritten")
                    touched, conflicts = _undo_conflicts(workspace_repo, repo_commits)
                    workspace_plans.append((path, workspace_repo, repo_commits, touched, conflicts))
                except Exception:
                    workspace_repo.close()
                    raise
            if any(plan[4] for plan in workspace_plans):
                conflicts = set().union(*(plan[4] for plan in workspace_plans))
                raise RuntimeError("These files have later changes by other runs and were left alone: "
                                   + ", ".join(sorted(conflicts)))

            commits = _run_commits(run_id)
            if not commits and not workspace_commits:
                raise ValueError(f"No saved changes were found for run {run_id}.")
            if commits and (_dirty_paths(r) & set().union(*(_commit_paths(c) for c in commits))):
                raise RuntimeError("vault has uncommitted changes; undo skipped so nothing is overwritten")
            vault_touched, vault_conflicts = _undo_conflicts(r, commits) if commits else (set(), set())
            if vault_conflicts:
                raise RuntimeError("These files have later changes by other runs and were left alone: "
                                   + ", ".join(sorted(vault_conflicts)))

            starts = [(workspace_repo, workspace_repo.head.commit.hexsha)
                      for _, workspace_repo, _, _, _ in workspace_plans]
            if commits:
                starts.append((r, r.head.commit.hexsha))
            index_backup = None
            if commits:
                db = vault._db()
                try:
                    index_backup = {
                        "fts": {path: db.execute("SELECT body FROM fts WHERE path=?", (path,)).fetchall()
                                for path in vault_touched},
                        "links": {path: db.execute("SELECT src, dst FROM links WHERE src=? OR dst=?", (path, path)).fetchall()
                                  for path in vault_touched},
                    }
                finally:
                    db.close()

            try:
                for path, workspace_repo, repo_commits, touched, _ in workspace_plans:
                    workspace_result = _apply_undo(workspace_repo, repo_commits, touched, "workspace", run_id)
                    workspace_result["workspace"] = os.path.basename(path)
                    workspace_results.append(workspace_result)
                if commits:
                    vault_result = _apply_undo(r, commits, vault_touched, "vault", run_id)
                    # Rebuildable indexes are projections. A bookkeeping failure
                    # must not roll back Git files behind an already-created HEAD.
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
            except Exception:
                for selected_repo, start in reversed(starts):
                    _rollback_repo(selected_repo, start)
                if commits:
                    try:
                        db = vault._db()
                        try:
                            for path in vault_touched:
                                db.execute("DELETE FROM fts WHERE path=?", (path,))
                                db.execute("DELETE FROM links WHERE src=? OR dst=?", (path, path))
                                for (body,) in index_backup["fts"][path]:
                                    db.execute("INSERT INTO fts VALUES (?,?)", (path, body))
                                for src, dst in index_backup["links"][path]:
                                    db.execute("INSERT INTO links VALUES (?,?)", (src, dst))
                            db.commit()
                        finally:
                            db.close()
                    except Exception:
                        pass
                raise
        finally:
            for _, workspace_repo, _, _, _ in workspace_plans:
                workspace_repo.close()

    workspace_result = {
        "reverted": [short for item in workspace_results for short in item["reverted"]],
        "new_commit": workspace_results[-1]["new_commit"] if workspace_results else "",
        "changes": sorted({path for item in workspace_results for path in item["changes"]}),
        "workspaces": workspace_results,
    }
    all_reverted = vault_result["reverted"] + workspace_result["reverted"]
    all_commits = ([vault_result["new_commit"]] if vault_result["new_commit"] else []) + [
        item["new_commit"] for item in workspace_results if item["new_commit"]
    ]
    return {"reverted": all_reverted, "new_commit": all_commits[-1] if all_commits else "",
            "vault": vault_result, "workspace": workspace_result}


def restore_flow(env_id: str, short_commit: str) -> str:
    """Read saved flow history under vault._lock, then save the selected version."""
    import app
    import runner
    import vault

    path = runner.env_path(env_id)
    vault.safe_path(path)
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", short_commit):
        raise ValueError("Enter at least 7 letters or numbers from the saved version ID.")
    try:
        with vault._lock:
            matches = list(vault._repo.iter_commits(paths=path))
            matching = [commit for commit in matches if commit.hexsha.startswith(short_commit.lower())]
            if not matching:
                raise ValueError(f"Saved version {short_commit} was not found for this flow.")
            if len(matching) > 1:
                raise ValueError("More than one saved version matches. Enter more of the version ID.")
            selected = matching[0]
            saved = selected.tree / path
            env = json.loads(saved.data_stream.read().decode("utf-8"))
    except ValueError:
        raise
    except KeyError:
        raise ValueError("That saved version does not contain this flow.")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("That saved flow version is not valid JSON.") from exc
    result = app.save_environment(env_id, env)
    return result["commit"]
