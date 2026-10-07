import importlib.util
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import threading


RUN_EVAL = Path(__file__).with_name("run_eval.py")
SPEC = importlib.util.spec_from_file_location("local_models_run_eval_test", RUN_EVAL)
run_eval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_eval)


class FakeOllama:
    def __init__(self, content="42"):
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                body = json.dumps({"message": {"content": content}, "prompt_eval_count": 5,
                                   "eval_count": 2, "eval_duration": 500_000_000}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def test_exact_match_checker_trims_and_ignores_case_only():
    assert run_eval.exact_match("  paris\n", "Paris") is True
    assert run_eval.exact_match("Paris.", "Paris") is False
    assert run_eval.exact_match("Paris, France", "Paris") is False


def test_eval_task_uses_glacier_local_ai_node_and_scores_independently(monkeypatch):
    with FakeOllama() as ollama:
        monkeypatch.setenv("GLACIER_OLLAMA_URL", ollama.url)
        result = run_eval.evaluate_task({"id": "addition", "prompt": "What is 19 + 23?", "expected": "42"}, "fake")

    assert result["passed"] is True
    assert ollama.requests[0]["model"] == "fake"
    assert ollama.requests[0]["options"] == {"temperature": 0}
    assert result["usage"]["tokens_out"] == 2
    assert result["usage"]["generation_seconds"] == 0.5


def test_report_includes_pass_counts_resource_and_task_rows():
    report = run_eval.render_results([{
        "model": "fake", "passed": 1, "total": 1, "peak_rss_kib": 1024,
        "tokens_per_second": 4.0, "seconds": 0.5, "wall_seconds": 1.0,
        "rows": [{"id": "addition", "expected": "42", "output": "42", "passed": True}],
    }])
    assert "1/1" in report
    assert "1.0 MiB" in report
    assert "4.00" in report
    assert "addition" in report


def test_task_checker_compares_json_values_and_lists_but_stays_strict():
    json_task = {"expected": "{\"name\":\"Mira Chen\",\"date\":\"2026-11-14\"}", "match": "json"}
    assert run_eval.task_passes('{"date": "2026-11-14", "name": "Mira Chen"}', json_task) is True
    assert run_eval.task_passes('{"name": "Mira"}', json_task) is False
    assert run_eval.task_passes("name: Mira Chen", json_task) is False
    list_task = {"expected": "apple,pear,plum", "match": "list"}
    assert run_eval.task_passes("apple, pear, plum", list_task) is True
    assert run_eval.task_passes("pear, apple, plum", list_task) is False
    assert run_eval.task_passes("Paris.", {"expected": "Paris"}) is False


def test_missing_field_task_really_has_one_missing_field():
    tasks = {t["id"]: t for t in json.loads((Path(run_eval.__file__).parent / "tasks.json").read_text())}
    assert "Friday" not in tasks["missing_field"]["prompt"]
