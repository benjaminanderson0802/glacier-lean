import store


def test_a_canceled_run_stays_canceled(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", store.DB)
    store.init(str(tmp_path / "runs.db"))
    store.create_run("r1", "flow", {"nodes": [], "edges": []})
    store.set_run("r1", "running")
    store.set_run("r1", "canceled")
    store.set_run("r1", "waiting", "approve")  # a step that was still finishing
    store.set_run("r1", "done")
    assert store.get_run("r1")["status"] == "canceled"


def test_other_status_changes_still_apply(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", store.DB)
    store.init(str(tmp_path / "runs.db"))
    store.create_run("r2", "flow", {"nodes": [], "edges": []})
    store.set_run("r2", "waiting", "a")
    store.set_run("r2", "running")
    store.set_run("r2", "done")
    assert store.get_run("r2")["status"] == "done"
