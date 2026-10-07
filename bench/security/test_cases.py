"""Acceptance checks for the security benchmark case corpus."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_case_files_have_unique_ids_and_expected_outcomes():
    cases = [json.loads(path.read_text()) for path in sorted((HERE / "cases").glob("*.json"))]
    assert len(cases) >= 20
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert set(case) == {"id", "title", "attack", "request", "expected"}
        assert case["id"] == next(path.stem for path in (HERE / "cases").glob(case["id"] + ".json"))
        assert case["expected"] == "blocked"
        assert isinstance(case["attack"], str) and case["attack"]
        assert isinstance(case["request"], dict)
        assert {"method", "path"} <= case["request"].keys()
        assert case["request"]["method"] in {"GET", "POST", "PUT", "OPTIONS"}
