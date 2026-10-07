"""Flow workspaces and the merge queue (roadmap: coding workers in isolated git worktrees; merge only when checks pass).
Every flow has a workspace folder GLACIER_HOME/workspaces/<flow>. Steps run there by default.
A flow with "isolate": true gets a private git worktree per run (GLACIER_HOME/worktrees/<flow>/<run>, branch run/<run>).
When the run is verified, its branch is merged into the workspace's main branch, one run at a time (a file lock is the
queue). When it is not, nothing reaches main; the branch is kept for inspection and the worktree is removed."""
import fcntl, os, subprocess

def _git(cwd, *args, check=True):
    p = subprocess.run(["git", "-c", "user.name=glacier", "-c", "user.email=glacier@localhost", *args], cwd=cwd,
                       capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {(p.stdout + p.stderr).strip()[-400:]}")
    return p.stdout.strip()


def base(home: str, env_id: str) -> str:
    return os.path.join(home, "workspaces", env_id)


def prepare(home: str, env_id: str, run_id: str, isolate: bool) -> str:
    """Returns the folder this run works in (idempotent: safe to call again after a crash)."""
    ws = base(home, env_id)
    os.makedirs(ws, exist_ok=True)
    if not isolate:
        return ws
    if not os.path.isdir(os.path.join(ws, ".git")):
        _git(ws, "init", "-q", "-b", "main")
    if not _git(ws, "rev-parse", "--verify", "-q", "HEAD", check=False):
        _git(ws, "add", "-A")
        _git(ws, "commit", "-q", "--allow-empty", "-m", "Glacier: workspace start")
    wt = os.path.join(home, "worktrees", env_id, run_id)
    if not os.path.isdir(wt):
        os.makedirs(os.path.dirname(wt), exist_ok=True)
        _git(ws, "worktree", "add", "-q", "-B", f"run/{run_id}", wt, "main")
    return wt


def finish(home: str, env_id: str, run_id: str, verified: bool) -> dict:
    """Commits the run's changes on its branch; merges into main only if verified (queued with a lock)."""
    ws = base(home, env_id)
    wt = os.path.join(home, "worktrees", env_id, run_id)
    branch = f"run/{run_id}"
    if os.path.isdir(wt):
        _git(wt, "add", "-A")
        if _git(wt, "status", "--porcelain"):
            _git(wt, "commit", "-q", "-m", f"Glacier run {run_id}")
    result = {"isolated": True, "branch": branch, "merged": False, "commit": "", "note": ""}
    if verified:
        with open(os.path.join(home, "worktrees", f"{env_id}.merge.lock"), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # the merge queue: one merge at a time per flow
            dirty = _git(ws, "status", "--porcelain")
            if dirty:
                result["note"] = "main has uncommitted changes; merge skipped so nothing is overwritten"
            else:
                p = subprocess.run(["git", "-c", "user.name=glacier", "-c", "user.email=glacier@localhost", "merge",
                                    "--no-ff", "-q", "-m", f"Glacier: merge verified run {run_id}", branch],
                                   cwd=ws, capture_output=True, text=True)
                if p.returncode == 0:
                    result.update(merged=True, commit=_git(ws, "rev-parse", "--short", "HEAD"))
                else:
                    _git(ws, "merge", "--abort", check=False)
                    result["note"] = "conflicts with work merged since this run started; branch kept for review"
    else:
        result["note"] = "not verified; nothing reached main, the branch is kept for inspection"
    if os.path.isdir(wt):
        _git(ws, "worktree", "remove", "--force", wt, check=False)
    return result
