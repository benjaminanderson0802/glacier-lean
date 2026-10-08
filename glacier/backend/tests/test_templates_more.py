"""End-to-end coverage for the six plain-language everyday templates."""

import http.server
import json
import os
from pathlib import Path
import socketserver
import threading
import time

from conftest import BACKEND


ROOT = Path(__file__).resolve().parents[3]
EXPECTED = {
    "tpl-document-note": ("notes/document-summary-", "document-summary.txt"),
    "tpl-downloads-tidy": ("downloads/review-", "older.txt"),
    "tpl-meeting-tasks": ("tasks/meeting-list-", "meeting-tasks.txt"),
    "tpl-web-change-watch": ("web-watch/run-status-", "web-status.txt"),
    "tpl-morning-brief": ("briefs/morning-brief-", "morning-brief.txt"),
    "tpl-backup-check": ("backups/check-", "backup-status.txt"),
}


class FakeOllama:
    def __init__(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                prompt = payload["messages"][-1]["content"].lower()
                if "meeting" in prompt or "checkbox" in prompt:
                    answer = "- [ ] Email the attendees\n- [ ] Book the room"
                elif "yesterday" in prompt or "notes changed" in prompt:
                    answer = "Yesterday's note: send the invoice."
                else:
                    answer = "Summary: the launch date is Friday."
                body = json.dumps({"message": {"content": answer}, "prompt_eval_count": 5, "eval_count": 8}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _by_id(server):
    available = {item["id"]: item for item in server.get("/api/templates")}
    manifest = json.loads((ROOT / "templates" / "manifest" / "MANIFEST.json").read_text())
    files = {entry["id"]: entry["file"] for entry in manifest["templates"]}
    for template_id in EXPECTED:
        available[template_id]["template"] = json.loads((ROOT / "templates" / files[template_id]).read_text())
    return {template_id: available[template_id] for template_id in EXPECTED}


def test_six_templates_validate_review_and_appear_in_gallery(server, monkeypatch, tmp_path):
    import template_registry
    import verify

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    templates = _by_id(server)
    assert set(templates) == set(EXPECTED)
    for item in templates.values():
        assert item["installable"] is True
        flow = item["template"]
        assert flow.get("description") and flow.get("when_to_use")
        verify.validate(flow.get("acceptance"))
        assert flow["acceptance"]
        review = template_registry.review_import(json.dumps({"glacier_flow": 1, "flow": flow}))
        assert review["accepted"] is True, review["review"]


def test_review_accepts_registered_plugin_step_and_rejects_unknown_step(tmp_path, monkeypatch):
    import template_registry

    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    flow = {
        "id": "plugin-review", "name": "Plugin review", "goal": "Read a document",
        "acceptance": [{"kind": "command", "cmd": "test -n 'summary'"}],
        "nodes": [{"id": "read", "type": "read_document", "config": {"source": "notes.txt"},
                   "position": {"x": 0, "y": 0}}],
        "edges": [],
    }
    review = template_registry.review_import(json.dumps({"glacier_flow": 1, "flow": flow}))
    assert review["accepted"] is True, review["review"]

    flow["nodes"][0]["type"] = "made_up_step"
    review = template_registry.review_import(json.dumps({"glacier_flow": 1, "flow": flow}))
    assert review["accepted"] is False
    assert any("unknown type" in finding for finding in review["review"])


def test_six_templates_run_with_user_settings_and_prove_real_outcomes(make_server, monkeypatch, tmp_path):
    # fetch_page normally refuses private addresses. This test-only resolver permits the local fixture server.
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "sitecustomize.py").write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(BACKEND)!r})\n"
        "import egress\n"
        "egress._resolve_public = lambda host: ['127.0.0.1']\n",
        encoding="utf-8",
    )
    previous_pythonpath = os.environ.get("PYTHONPATH", "")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [str(shim), str(BACKEND), previous_pythonpath])))

    class Page(http.server.BaseHTTPRequestHandler):
        text = "Version one"

        def do_GET(self):
            body = f"<html><body><p>{type(self).text}</p></body></html>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    with FakeOllama() as ollama, socketserver.TCPServer(("127.0.0.1", 0), Page) as page_server:
        page_thread = threading.Thread(target=page_server.serve_forever, daemon=True)
        page_thread.start()
        monkeypatch.setenv("GLACIER_OLLAMA_URL", ollama.url)
        server = make_server().start()
        templates = _by_id(server)
        try:
            for template_id, item in templates.items():
                flow = json.loads(json.dumps(item["template"]))
                nodes = {node["id"]: node for node in flow["nodes"]}
                home = Path(server.home)
                workspace = home / "workspaces" / template_id

                if template_id == "tpl-document-note":
                    source = workspace / "test documents" / "notes for today.txt"
                    source.parent.mkdir(parents=True)
                    source.write_text("A private fixture document with no required magic words.")
                    nodes["read_document"]["config"]["source"] = str(source)
                    nodes["save_note"]["config"]["template"] = "# Document summary\n\nRun {run}\n{prev_output}"
                elif template_id == "tpl-downloads-tidy":
                    downloads = home / "My Downloads Folder"
                    downloads.mkdir()
                    old = downloads / "older file.txt"
                    old.write_text("old download")
                    old_time = time.time() - 10 * 24 * 60 * 60
                    os.utime(old, (old_time, old_time))
                    nodes["list_old"]["config"]["cmd"] = f'find "{downloads}" -type f -mtime +7 -print'
                    nodes["move_approved"]["config"]["cmd"] = f'mkdir -p "{downloads.parent / "Downloads Review"}" && find "{downloads}" -type f -mtime +7 -print0 | xargs -0 -I{{}} mv -- "{{}}" "{downloads.parent / "Downloads Review"}/"'
                elif template_id == "tpl-meeting-tasks":
                    source = workspace / "my meeting notes.txt"
                    workspace.mkdir(parents=True, exist_ok=True)
                    source.write_text("Email the attendees and book the room.")
                    nodes["read_notes"]["config"]["source"] = str(source)
                    nodes["save_tasks"]["config"]["template"] = "# Meeting tasks\n\nRun {run}\n{prev_output}"
                elif template_id == "tpl-web-change-watch":
                    host, port = page_server.server_address
                    nodes["read_page"]["config"]["url"] = f"http://{host}:{port}/page"
                    nodes["read_page"]["config"]["allowed_sites"] = host
                    nodes["compare_page"]["config"]["cmd"] = (
                        'if test -f "$GLACIER_HOME/vault/web-watch/last-page.md" && '
                        'cmp -s "$GLACIER_HOME/vault/web-watch/last-page.md" "$GLACIER_HOME/vault/web-watch/current-page.md"; '
                        'then printf "No change\n" > "$GLACIER_HOME/vault/web-watch/web-status.txt"; '
                        'else printf "Page changed\n" > "$GLACIER_HOME/vault/web-watch/web-status.txt"; fi; '
                        'cp "$GLACIER_HOME/vault/web-watch/current-page.md" "$GLACIER_HOME/vault/web-watch/last-page.md"; '
                        'cat "$GLACIER_HOME/vault/web-watch/web-status.txt"'
                    )
                elif template_id == "tpl-morning-brief":
                    note = home / "vault" / "journal" / "yesterday.md"
                    note.parent.mkdir(parents=True)
                    note.write_text("A private note with no required magic words.")
                    old_time = time.time() - 36 * 60 * 60
                    os.utime(note, (old_time, old_time))
                    nodes["save_brief"]["config"]["template"] = "# Morning brief\n\nRun {run}\n{prev_output}"
                elif template_id == "tpl-backup-check":
                    backups = home / "My Backup Folder"
                    backups.mkdir()
                    # No recent file: a stale backup is a successful recorded finding.
                    old = backups / "old archive.zip"
                    old.write_text("backup")
                    old_time = time.time() - 5 * 24 * 60 * 60
                    os.utime(old, (old_time, old_time))
                    nodes["check_recent_file"]["config"]["cmd"] = (
                        f'newest=$(find "{backups}" -type f -mtime -2 -print -quit); '
                        'if test -n "$newest"; '
                        'then printf "A recent backup was found: %s\\n" "$newest"; '
                        'else printf "Alert: backups are stale; check the backup schedule and folder.\\n"; fi'
                    )

                server.put(f"/api/environments/{template_id}", flow)
                run_id = server.post(f"/api/environments/{template_id}/run")["run_id"]
                run = server.get(f"/api/runs/{run_id}")
                if template_id == "tpl-downloads-tidy":
                    deadline = time.time() + 30
                    while time.time() < deadline:
                        run = server.get(f"/api/runs/{run_id}")
                        if run["node_states"].get("approve_move") == "waiting":
                            break
                        time.sleep(0.2)
                    assert run["node_states"]["approve_move"] == "waiting"
                    assert old.exists()
                    server.post(f"/api/runs/{run_id}/approve", {"node_id": "approve_move", "approved": True})
                run = server.wait_run(run_id)
                assert run["status"] == "done", (template_id, run)
                assert run["verification"] and all(check["passed"] for check in run["verification"]), (template_id, run["verification"])

                note_prefix, _artifact = EXPECTED[template_id]
                note_dir = home / "vault" / Path(note_prefix).parent
                if template_id == "tpl-downloads-tidy":
                    note_path = note_dir / f"review-{run_id}.md"
                    assert not old.exists()
                    assert (downloads.parent / "Downloads Review" / old.name).is_file()
                elif template_id == "tpl-web-change-watch":
                    note_path = note_dir / f"run-status-{run_id}.md"
                elif template_id == "tpl-backup-check":
                    note_path = note_dir / f"status-{run_id}.md"
                    assert "alert" in note_path.read_text(encoding="utf-8").lower()
                else:
                    note_path = note_dir / f"{Path(note_prefix).name}{run_id}.md"
                assert note_path.is_file(), (template_id, note_path)
                body = note_path.read_text(encoding="utf-8")
                assert body.strip(), (template_id, body)
                if template_id == "tpl-meeting-tasks":
                    assert "- [ ]" in body or "no tasks" in body.lower()
                if template_id == "tpl-morning-brief":
                    assert body.strip() or "no notes" in body.lower()

            # A second tidy run declined at approval: nothing moves and nothing is deleted.
            flow = json.loads(json.dumps(templates["tpl-downloads-tidy"]["template"]))
            downloads = home / "Another Downloads Folder"
            downloads.mkdir()
            declined_file = downloads / "keep me.txt"
            declined_file.write_text("leave in place")
            old_time = time.time() - 10 * 24 * 60 * 60
            os.utime(declined_file, (old_time, old_time))
            nodes = {node["id"]: node for node in flow["nodes"]}
            nodes["list_old"]["config"]["cmd"] = f'find "{downloads}" -type f -mtime +7 -print'
            nodes["move_approved"]["config"]["cmd"] = f'mkdir -p "{downloads.parent / "Downloads Review"}" && find "{downloads}" -type f -mtime +7 -print0 | xargs -0 -I{{}} mv -- "{{}}" "{downloads.parent / "Downloads Review"}/"'
            server.put("/api/environments/tpl-downloads-declined", flow)
            run_id = server.post("/api/environments/tpl-downloads-declined/run")["run_id"]
            deadline = time.time() + 30
            while time.time() < deadline:
                run = server.get(f"/api/runs/{run_id}")
                if run["node_states"].get("approve_move") == "waiting":
                    break
                time.sleep(0.2)
            server.post(f"/api/runs/{run_id}/approve", {"node_id": "approve_move", "approved": False})
            run = server.wait_run(run_id)
            assert run["status"] == "done"
            assert all(check["passed"] for check in run["verification"])
            assert declined_file.is_file()
            assert not (downloads.parent / "Downloads Review" / declined_file.name).exists()
        finally:
            server.stop()
            page_server.shutdown()
            page_thread.join(timeout=2)
            page_server.server_close()
