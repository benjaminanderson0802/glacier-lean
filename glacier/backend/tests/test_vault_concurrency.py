"""Stress the real API's vault Git access while notes are being written."""
import pytest
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
                restore_response = httpx.post(server.url + f"/api/environments/{base}-flow/restore",
                                              timeout=10, json={"commit": old_commit})
                assert restore_response.status_code == 200, restore_response.text  # same check, with the reason shown

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


@pytest.mark.serial  # timing/stress: runs alone, after the parallel batch
def test_concurrent_vault_api_reads_and_writes(server, tmp_path):
    # Repeat within one acceptance test to expose process-local GitPython pipe races.
    for round_number in range(3):
        _round(server, round_number)


def test_shared_vault_repo_access_is_locked_or_documented():
    """Scan all backend source for shared Repo use without an enclosing vault lock."""
    import re

    backend = Path(__file__).resolve().parents[1]
    pattern = re.compile(r"\b_repo\.|\brepo\(\)|vault\.repo")
    offenders = []
    allowlisted = {
        "rollback.py": {"repo", "_run_commits", "_undo_conflicts", "undo", "restore_flow"},
    }

    for path in backend.rglob("*.py"):
        if "tests" in path.relative_to(backend).parts:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        active_function = None
        function_indent = -1
        lock_indent = None
        for number, line in enumerate(lines, 1):
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            if stripped.startswith(("def ", "async def ")):
                function_indent = indent
                active_function = stripped.split("def ", 1)[1].split("(", 1)[0]
                lock_indent = None
            elif stripped and indent <= function_indent:
                active_function = None
                function_indent = -1
                lock_indent = None
            if lock_indent is not None and indent <= lock_indent:
                lock_indent = None
            if stripped.startswith("with ") and "_lock" in stripped and stripped.endswith(":"):
                lock_indent = indent
            if pattern.search(line):
                helper_ok = path.name in allowlisted and active_function in allowlisted[path.name]
                if lock_indent is None and not helper_ok:
                    offenders.append(f"{path.relative_to(backend)}:{number}: {stripped}")
    assert not offenders, "Shared vault Repo access must hold vault._lock:\n" + "\n".join(offenders)
