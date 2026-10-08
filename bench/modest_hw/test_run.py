"""Offline checks for the modest-hardware benchmark parser and report."""
import importlib.util
from pathlib import Path
import re


RUN = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("modest_hw_run", RUN)
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


def test_rss_parser_sums_backend_and_ollama_runner_samples():
    sample = {"backend": 120 * 1024, "ollama": 700 * 1024}
    assert run.peak_process_rss(sample) == 820 * 1024


def test_acceptance_checks_cover_expected_output_shapes():
    assert run.check_output("sum", "42", "42")
    assert not run.check_output("sum", "41", "42")
    assert run.check_output("contains", "A short summary of the report", "summary")
    assert run.check_output("list_items", "- Call Lee\n- Send draft", "Call Lee|Send draft")
    assert not run.check_output("list_items", "- Call Lee", "Call Lee|Send draft")


def test_classification_task_has_clear_rules_and_constrained_labels():
    task = next(item for item in run.AUTOMATIONS if item["id"] == "classify_messages")
    assert "A refund, invoice amount, duplicate charge, or billing date is billing" in task["prompt"]
    assert task["choose_one"] == "billing, technical, sales"
    assert task["expected"].split("|")[8] == "billing"


def test_report_has_plain_language_summary_and_all_tables():
    report = run.render_markdown({
        "machine": {"cpu_cores_reported": 4, "cpu_cores_detected": 16, "memory_gb": 7},
        "modes": [{"mode": "light", "model": "qwen3:0.6b", "max_parallel_runs": 1, "startup_seconds": 2.3,
                   "idle_backend_rss_mib": 90, "runs": [], "memory": {}, "usability": {}}],
    })
    assert report.startswith("On a 4-core laptop with 7 GB memory,")
    for expected in ("Start-up", "Automation runs", "Memory screen", "Usability", "qwen3:0.6b"):
        assert expected in report
    assert "CPU percentages use all detected logical CPUs" in report


def test_cpu_delta_is_percent_of_aggregate_counter_interval():
    assert run.cpu_percent({"idle": 10, "total": 20}, {"idle": 15, "total": 40}) == 75


def test_fake_run_response_is_parsed_without_a_model():
    done = run.parse_run_result({"status": "done", "outputs": {"local_ai": "42"}})
    assert done == {"status": "done", "output": "42", "error": ""}
    failed = run.parse_run_result({"status": "failed", "outputs": {"local_ai": "model unavailable"}})
    assert failed["error"] == "model unavailable"


def test_generated_upload_pdf_has_twenty_pages(tmp_path):
    path = run.synthetic_pdf(tmp_path / "test.pdf", pages=20)
    contents = path.read_bytes()
    assert contents.startswith(b"%PDF-1.4")
    assert len(re.findall(rb"/Type /Page\b", contents)) == 20
