import importlib.util
from pathlib import Path


BENCH_RUNNER = Path(__file__).parents[1] / "bench" / "run_benchmark.py"
SPEC = importlib.util.spec_from_file_location("recall_benchmark_runner", BENCH_RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_benchmark_reports_false_negatives_false_positives_and_uncertain():
    cases = [
        {"case_id": "R001", "label": "recalled", "brand": "Acme", "model": "A1", "model_year": "2024", "expected": "match", "recall_number": "24V000001", "source_url": "https://www.nhtsa.gov/recalls?nhtsaId=24V000001"},
        {"case_id": "R002", "label": "recalled", "brand": "Acme", "model": "A2", "model_year": "2024", "expected": "match", "recall_number": "24V000002", "source_url": "https://www.nhtsa.gov/recalls?nhtsaId=24V000002"},
        {"case_id": "C001", "label": "clean", "brand": "Elsewhere", "model": "B1", "model_year": "2024", "expected": "no_match", "recall_number": "", "source_url": "https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip"},
    ]
    recalls = [{"source_id": "nhtsa_recalls", "record_id": "24V000001", "data": {"CAMPNO": "24V000001", "MAKETXT": "Acme", "MODELTXT": "A1", "YEARTXT": "2024"}}]
    result = MODULE.evaluate(cases, recalls, as_of="2026-10-10")
    assert result["counts"]["false_negative"] == 1
    assert result["counts"]["false_positive"] == 0
    assert result["false_negatives"][0]["case_id"] == "R002"
    assert result["within_at_most_one_percent_false_no_match_gate"] is False
