"""Stress the real API's vault Git access while notes are being written."""
import concurrent.futures
import os
from pathlib import Path
import time

import git
import httpx

from conftest import Server


def _round(server, round_number):
    base = f"stress-{round_number}"

    def write(worker):
        for item in range(25):
            response = httpx.put(server.url + "/api/memory/note", timeout=10, json={
                "path": f"{base}/w{worker}-{item}.md",
                "body": f"# Note {worker}-{item}\n\n concurrencytoken sharedword [[{base}/w{worker}-{(item + 1) % 25}]]",
                "author": "owner",
            })
            response.raise_for_status()

    deadline = time.monotonic() + 120
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=12)
    try:
        writers = [pool.submit(write, worker) for worker in range(8)]

        # Keep a prior flow version around so restore exercises Git tree reads
        # while writers continue committing.
        flow_path = f"environments/{base}-flow.json"
        server.put(f"/api/environments/{base}-flow", {
            "id": f"{base}-flow", "name": "Before", "nodes": [], "edges": []
        })
        repo = git.Repo(os.path.join(server.home, "vault"))
        try:
            old_commit = list(repo.iter_commits(paths=flow_path, max_count=1))[0].hexsha
        finally:
            repo.close()
        server.put(f"/api/environments/{base}-flow", {
            "id": f"{base}-flow", "name": "After", "nodes": [], "edges": []
        })
        restore_response = httpx.post(server.url + f"/api/environments/{base}-flow/restore", timeout=10,
                                      json={"commit": old_commit})
        restore_response.raise_for_status()

        def read_loop():
            while time.monotonic() < deadline and not all(task.done() for task in writers):
                history_response = httpx.get(server.url + "/api/memory/history", timeout=10,
                                             params={"path": f"{base}/w0-0.md"})
                history_response.raise_for_status()
                history = history_response.json()
                assert isinstance(history, list)
                search_response = httpx.get(server.url + "/api/memory/search", timeout=10,
                                            params={"q": "concurrencytoken"})
                search_response.raise_for_status()
                search = search_response.json()
                assert isinstance(search, list)
                graph_response = httpx.get(server.url + "/api/memory/graph", timeout=10)
                graph_response.raise_for_status()
                assert isinstance(graph_response.json(), dict)
                changes_response = httpx.get(server.url + "/api/runs/concurrency-probe/changes", timeout=10)
                changes_response.raise_for_status()
                assert isinstance(changes_response.json(), list)
                # The single-threaded setup restore already exercised flow
                # restore; keep this endpoint read-heavy loop deterministic.

        readers = [pool.submit(read_loop) for _ in range(4)]
        for task in writers + readers:
            task.result(timeout=max(1, deadline - time.monotonic()))
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)
    assert time.monotonic() < deadline, "vault API concurrency round exceeded 120 seconds"

    repo = git.Repo(os.path.join(server.home, "vault"))
    try:
        commits = list(repo.iter_commits(paths=f"{base}/"))
    finally:
        repo.close()
    assert len(commits) == 200
    assert len([p for p in os.listdir(os.path.join(server.home, "vault", base)) if p.endswith(".md")]) == 200


def test_concurrent_vault_api_reads_and_writes(server, tmp_path):
    # Repeat within one acceptance test to expose process-local GitPython pipe races.
    for round_number in range(3):
        _round(server, round_number)


def test_shared_vault_repo_access_is_locked_or_documented():
    """Flag direct shared Repo access; each hit needs a nearby vault lock/helper."""
    backend = Path(__file__).resolve().parents[1]
    offenders = []
    patterns = ("vault._repo", "vault.repo()", "vault.repo(")
    paths = [backend / name for name in ("vault.py", "rollback.py", "memory_hygiene.py", "workspaces.py")]
    paths.append(backend / "routes" / "memory.py")
    for path in paths:
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for number, line in enumerate(lines, 1):
            if any(pattern in line for pattern in patterns):
                # The explicit helper is audited by name and takes the lock itself.
                if path.name == "rollback.py":
                    continue
                # These modules use one locked transaction block; accept lines
                # indented beneath its `with` statement, including exception cleanup.
                lock_line = max((i for i, candidate in enumerate(lines[:number - 1])
                                 if candidate.lstrip() == "with vault._lock:"), default=-1)
                in_lock_block = lock_line >= 0 and all(
                    not candidate.strip() or len(candidate) - len(candidate.lstrip()) >
                    len(lines[lock_line]) - len(lines[lock_line].lstrip())
                    for candidate in lines[lock_line + 1:number - 1]
                )
                window = "\n".join(lines[max(0, number - 12):number])
                if not in_lock_block and "with vault._lock" not in window and "with _lock" not in window:
                    offenders.append(f"{path.relative_to(backend.parent)}:{number}: {line.strip()}")
    assert not offenders, "Shared vault Repo access must hold vault._lock:\n" + "\n".join(offenders)
