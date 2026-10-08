import sqlite3
import threading
import time

import store


def test_sqlite_wait_does_not_hold_up_run_status_reads(tmp_path, monkeypatch):
    db_path = str(tmp_path / "runs.sqlite")
    store.init(db_path)
    store.create_run("run-1", "flow", {"nodes": []})

    blocker = sqlite3.connect(db_path, timeout=1)
    blocker.execute("BEGIN IMMEDIATE")
    connecting = threading.Event()
    connect = store.sqlite3.connect

    def observed_connect(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connecting.set()
        return connection

    monkeypatch.setattr(store.sqlite3, "connect", observed_connect)
    writer = threading.Thread(target=store.set_run, args=("run-1", "done"))
    writer.start()
    assert connecting.wait(2), "status writer did not open its SQLite connection"
    time.sleep(0.05)

    started = time.monotonic()
    run = store.get_run("run-1")
    read_seconds = time.monotonic() - started

    blocker.rollback()
    blocker.close()
    writer.join(2)
    assert not writer.is_alive(), "status writer stayed blocked after SQLite unlocked"
    assert run["status"] == "running"
    assert read_seconds < 0.5
    assert store.get_run("run-1")["status"] == "done"
