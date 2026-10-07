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
    "tpl-document-note": ("notes/document-summary.md", "document-summary.txt"),
    "tpl-downloads-tidy": ("downloads/review-", "Downloads-review/older.txt"),
    "tpl-meeting-tasks": ("tasks/meeting-list.md", "meeting-tasks.txt"),
    "tpl-web-change-watch": ("web-watch/changed-", "web-status.txt"),
    "tpl-morning-brief": ("briefs/morning-brief.md", "morning-brief.txt"),
    "tpl-backup-check": ("backups/check-", "backup-status.txt"),
}


class FakeOllama:
    def __init__(self):
        owner = self

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


def test_six_templates_install_run_verify_and_write_expected_notes(make_server, monkeypatch, tmp_path):
    # fetch_page normally refuses private addresses. The test server is deliberately local;
    # this test-only resolver maps the allowed test hostname to that local server.
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
                    (workspace / "documents").mkdir(parents=True)
                    (workspace / "documents" / "input.txt").write_text("Project launch is Friday.")
                    # Start with an empty age threshold fixture; the flow reads the file above.
                elif template_id == "tpl-downloads-tidy":
                    (workspace / "Downloads").mkdir(parents=True)
                    old = workspace / "Downloads" / "older.txt"
                    old.write_text("old download")
                    old_time = time.time() - 10 * 24 * 60 * 60
                    os.utime(old, (old_time, old_time))
                elif template_id == "tpl-meeting-tasks":
                    (workspace / "documents").mkdir(parents=True)
                    (workspace / "documents" / "meeting-notes.txt").write_text(
                        "Email the attendees and book the room."
                    )
                elif template_id == "tpl-web-change-watch":
                    host, port = page_server.server_address
                    nodes["read_page"]["config"]["url"] = f"http://{host}:{port}/page"
                    nodes["read_page"]["config"]["allowed_sites"] = host
                    # Seed the last saved copy so the first run proves that changes are detected.
                    last = home / "vault" / "web-watch" / "last-page.md"
                    last.parent.mkdir(parents=True)
                    last.write_text("Version zero")
                elif template_id == "tpl-morning-brief":
                    note = home / "vault" / "journal" / "yesterday.md"
                    note.parent.mkdir(parents=True)
                    note.write_text("Send the invoice to Acme.")
                    old_time = time.time() - 36 * 60 * 60
                    os.utime(note, (old_time, old_time))
                elif template_id == "tpl-backup-check":
                    (workspace / "backups").mkdir(parents=True)
                    (workspace / "backups" / "latest.zip").write_text("backup")

                server.put(f"/api/environments/{template_id}", flow)
                run_id = server.post(f"/api/environments/{template_id}/run")["run_id"]
                run = server.get(f"/api/runs/{run_id}")
                if template_id == "tpl-downloads-tidy":
                    # Nothing moves until the owner approves the proposed review list.
                    deadline = time.time() + 30
                    while time.time() < deadline:
                        run = server.get(f"/api/runs/{run_id}")
                        if run["node_states"].get("approve_move") == "waiting":
                            break
                        time.sleep(0.2)
                    assert run["node_states"]["approve_move"] == "waiting"
                    assert (workspace / "Downloads" / "older.txt").exists()
                    server.post(f"/api/runs/{run_id}/approve", {"node_id": "approve_move", "approved": True})
                run = server.wait_run(run_id)
                assert run["status"] == "done", (template_id, run)
                assert run["verification"] and all(check["passed"] for check in run["verification"]), (template_id, run["verification"])

                note_prefix, artifact = EXPECTED[template_id]
                note_path = home / "vault" / note_prefix
                if template_id == "tpl-downloads-tidy":
                    note_path = next((home / "vault" / "downloads").glob("review-*.md"))
                elif template_id == "tpl-web-change-watch":
                    note_path = next((home / "vault" / "web-watch").glob("changed-*.md"))
                    Page.text = "Version two"
                elif template_id == "tpl-backup-check":
                    note_path = next((home / "vault" / "backups").glob("check-*.md"))
                assert note_path.is_file(), (template_id, note_path)
                body = note_path.read_text(encoding="utf-8")
                expected_text = {
                    "tpl-document-note": "Friday",
                    "tpl-downloads-tidy": "older.txt",
                    "tpl-meeting-tasks": "[ ]",
                    "tpl-web-change-watch": "changed",
                    "tpl-morning-brief": "invoice",
                    "tpl-backup-check": "backup",
                }[template_id]
                assert expected_text.casefold() in body.casefold(), (template_id, body)
                if template_id == "tpl-downloads-tidy":
                    assert (workspace / artifact).is_file()
        finally:
            server.stop()
            page_server.shutdown()
            page_thread.join(timeout=2)
            page_server.server_close()
