"""Stress the real API's vault Git access while notes are being written."""
import concurrent.futures
import os
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
