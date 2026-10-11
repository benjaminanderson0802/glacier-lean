"""Acceptance coverage for installed venture manifests and their human steps."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from conftest import env


def _manifest(home):
    folder = Path(home) / "ventures" / "truck-dispatch"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "slug": "truck-dispatch",
        "name": "Truck dispatch",
        "flows": [{"env_id": "dispatch", "dry_run_env_id": "dispatch-preview"}],
        "schedule": {"cron": "0 8 * * *"},
        "daily_report": "reports/today.json",
        "secrets": [{"name": "FLEET_KEY", "label": "Fleet key"}],
        "your_steps": [{"id": "fleet-key", "title": "Paste the fleet key", "instructions": "Add it from the fleet portal.",
                        "secret_name": "FLEET_KEY", "link": "https://fleet.example.test/settings/api"}],
    }
    (folder / "venture.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_ventures_reads_installed_manifest_and_today_run_state(server):
    _manifest(server.home)
    report = Path(server.home) / "ventures" / "truck-dispatch" / "reports" / "today.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({"date": datetime.now(timezone.utc).date().isoformat(), "counts": {"loads_dispatched": 3}}), encoding="utf-8")
    server.put("/api/environments/dispatch", env("dispatch", [
        ("start", "schedule", {"cron": "0 8 * * *"}),
        ("work", "command", {"cmd": "echo delivered 3"}),
    ], [("start", "work", "")]))
    server.put("/api/environments/dispatch-preview", env("dispatch-preview", [
        ("work", "command", {"cmd": "echo preview only"}),
    ], []))
    run_id = server.post("/api/environments/dispatch/run")["run_id"]
    server.wait_run(run_id)

    rows = server.get("/api/ventures")

    # A fresh Glacier home now contains the bundled venture portfolio as well
    # as this test fixture, so locate the venture under test by its slug.
    venture = next(row for row in rows if row["slug"] == "truck-dispatch")
    assert venture["slug"] == "truck-dispatch"
    assert venture["status"] == "setting_up"
    assert venture["today"]["runs"] == 1 and venture["today"]["completed"] == 1
    assert venture["today"]["loads_dispatched"] == 3
    assert venture["next_run"]
    assert venture["your_steps"][0]["done"] is False
    digest = server.get("/api/home")["venture_digest"]
    assert digest["ventures"] >= 1 and digest["runs"] == 1 and digest["completed"] == 1
    assert digest["failed"] == 0 and digest["waiting_for_you"] >= 1


def test_venture_your_steps_appear_in_home_and_approval_wait_can_resume(server):
    _manifest(__import__("pathlib").Path(server.home))
    approval_flow = env("dispatch", [
        ("approval", "approval", {"prompt": "Your step: review the dispatch list"}),
        ("work", "command", {"cmd": "echo resumed"}),
    ], [("approval", "work", "yes")])
    server.put("/api/environments/dispatch", approval_flow)
    run_id = server.post("/api/environments/dispatch/run")["run_id"]
    waiting = server.wait_run(run_id, ("waiting",))
    home = server.get("/api/home")
    assert any(item["kind"] == "your_step" and item["ref"].get("step_id") == "fleet-key"
               for item in home["venture_steps"])
    assert any(item["kind"] == "your_step" and item.get("title", "").lower().startswith("your step:")
               for item in home["venture_steps"]), home["venture_steps"]

    assert server.post(f"/api/runs/{run_id}/approve", {"node_id": waiting["waiting_on"], "approved": True}) == {"ok": True}
    assert server.wait_run(run_id)["status"] == "done"


def test_venture_pause_resume_and_dry_run_use_manifest_flow_ids(server):
    _manifest(__import__("pathlib").Path(server.home))
    server.put("/api/environments/dispatch", env("dispatch", [
        ("start", "schedule", {"cron": "0 8 * * *"}), ("work", "command", {"cmd": "echo live"}),
    ], [("start", "work", "")]))
    server.put("/api/environments/dispatch-preview", env("dispatch-preview", [
        ("work", "command", {"cmd": "echo preview only"}),
    ], []))

    paused = server.post("/api/ventures/truck-dispatch/pause")
    assert paused["paused"] is True
    assert server.get("/api/environments/dispatch")["enabled"] is False
    resumed = server.post("/api/ventures/truck-dispatch/resume")
    assert resumed["paused"] is False
    assert server.get("/api/environments/dispatch")["enabled"] is True
    run = server.post("/api/ventures/truck-dispatch/run", {"dry_run": True})
    completed = server.wait_run(run["run_id"])
    assert completed["env_id"] == "dispatch-preview"
    assert "preview only" in completed["outputs"]["work"]


def test_paused_venture_schedules_do_not_start_and_resume_together(server):
    _manifest(server.home)
    for env_id in ("dispatch", "dispatch-preview"):
        server.put(f"/api/environments/{env_id}", env(env_id, [
            ("start", "schedule", {"cron": "* * * * * *"}),
            ("work", "command", {"cmd": "echo scheduled"}),
        ], [("start", "work", "")]))
    server.post("/api/ventures/truck-dispatch/pause")
    time.sleep(2.5)
    assert server.get("/api/runs?env_id=dispatch") == []
    assert server.get("/api/runs?env_id=dispatch-preview") == []

    server.post("/api/ventures/truck-dispatch/resume")
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if all(server.get(f"/api/runs?env_id={env_id}") for env_id in ("dispatch", "dispatch-preview")):
            break
        time.sleep(0.25)
    assert server.get("/api/runs?env_id=dispatch")
    assert server.get("/api/runs?env_id=dispatch-preview")


def test_venture_setup_secret_is_saved_and_done_is_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    _manifest(tmp_path)
    import secrets_store
    from routes import ventures
    saved = []
    monkeypatch.setattr(secrets_store, "set", lambda name, value: saved.append((name, value)))
    app = FastAPI(); app.include_router(ventures.router)
    client = TestClient(app)
    secret = "private-fleet-token-890"
    response = client.post("/api/ventures/truck-dispatch/steps/fleet-key/done", json={"value": secret})
    result = response.json()
    assert response.status_code == 200
    assert result["done"] is True and secret not in response.text
    assert saved == [("FLEET_KEY", secret)]
    assert secret not in (tmp_path / "ventures" / "truck-dispatch" / "progress.json").read_text()
    steps = client.get("/api/ventures").json()[0]["your_steps"]
    assert steps[0]["done"] is True
    assert steps[0].get("secret_name") == "FLEET_KEY"


def test_venture_setup_secret_bundle_is_saved_once_and_never_echoed(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    manifest = _manifest(tmp_path)
    manifest["your_steps"][0]["secrets"] = [
        {"name": "CLIENT_ID", "label": "App ID"},
        {"name": "CLIENT_SECRET", "label": "App secret"},
    ]
    path = Path(tmp_path) / "ventures" / "truck-dispatch" / "venture.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    import secrets_store
    from routes import ventures
    saved = []
    monkeypatch.setattr(secrets_store, "set", lambda name, value: saved.append((name, value)))
    app = FastAPI(); app.include_router(ventures.router)
    client = TestClient(app)
    values = {"CLIENT_ID": "private-id", "CLIENT_SECRET": "private-secret"}

    response = client.post("/api/ventures/truck-dispatch/steps/fleet-key/done", json={"values": values})
    assert response.status_code == 200
    assert response.json()["secret_names"] == ["CLIENT_ID", "CLIENT_SECRET"]
    assert "private-id" not in response.text and "private-secret" not in response.text
    assert saved == list(values.items())
    assert "private-secret" not in path.with_name("progress.json").read_text()

    again = client.post("/api/ventures/truck-dispatch/steps/fleet-key/done", json={"values": {"CLIENT_ID": "changed", "CLIENT_SECRET": "changed"}})
    assert again.status_code == 200
    assert saved == list(values.items())


def test_install_manifests_copies_new_bundled_ventures_without_overwriting(tmp_path):
    from routes.ventures import install_manifests
    bundled, home = tmp_path / "bundle" / "ventures", tmp_path / "home"
    for slug, body in (("truck-dispatch", {"name": "new"}), ("property-appeal", {"name": "appeal"})):
        folder = bundled / slug
        folder.mkdir(parents=True)
        (folder / "venture.json").write_text(json.dumps(body), encoding="utf-8")
    existing = home / "ventures" / "truck-dispatch" / "venture.json"
    existing.parent.mkdir(parents=True)
    existing.write_text('{"name":"owner copy"}', encoding="utf-8")

    install_manifests(str(home), bundled)
    install_manifests(str(home), bundled)

    assert json.loads(existing.read_text(encoding="utf-8")) == {"name": "owner copy"}
    copied = home / "ventures" / "property-appeal" / "venture.json"
    assert json.loads(copied.read_text(encoding="utf-8")) == {"name": "appeal"}
