"""Flow workspaces and the merge queue (roadmap: coding workers in isolated git worktrees; merge only when checks pass).
Every flow has a workspace folder GLACIER_HOME/workspaces/<flow>. Steps run there by default.
A flow with "isolate": true gets a private git worktree per run (GLACIER_HOME/worktrees/<flow>/<run>, branch run/<run>).
When the run is verified, its branch is merged into the workspace's main branch, one run at a time (a file lock is the
queue). When it is not, nothing reaches main; the branch is kept for inspection and the worktree is removed."""
# Lock order for code that needs both locks: vault._lock, then the per-flow merge
# lock. This merge operates only on the separate workspace repository, so it
# takes only the merge lock and never acquires vault._lock while holding it.
import os, subprocess, time

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class _MergeLock:
    """Cross-process lock for the per-flow merge queue."""
    def __init__(self, file):
        self.file = file

    def __enter__(self):
        if os.name == "nt":
            self.file.seek(0)
            if not self.file.read(1):
                self.file.seek(0)
                self.file.write("0")
                self.file.flush()
            self.file.seek(0)
            while True:
                try:
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        else:
            fcntl.flock(self.file, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_):
        try:
            if os.name == "nt":
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.file, fcntl.LOCK_UN)
        finally:
            self.file.close()

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
        with _MergeLock(open(os.path.join(home, "worktrees", f"{env_id}.merge.lock"), "a+")):
            dirty = _git(ws, "status", "--porcelain")
            if dirty:
                result["note"] = "main has uncommitted changes; merge skipped so nothing is overwritten"
            else:
                p = subprocess.run(["git", "-c", "user.name=glacier", "-c", "user.email=glacier@localhost", "merge",
                                    "--no-ff", "-q", "-m", f"[run:{run_id}] Glacier: merge verified run {run_id}", branch],
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
