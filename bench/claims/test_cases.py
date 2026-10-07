"""Acceptance checks for the seeded claim benchmark cases."""

import importlib.util
from pathlib import Path

_PATH = Path(__file__).with_name("run_claims.py")
_SPEC = importlib.util.spec_from_file_location("claims_bench_cases_test_unique", _PATH)
run_claims = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_claims)


def test_cases_have_known_safe_outcomes():
    cases = run_claims.load_cases(Path(__file__).parent / "cases.json")

    assert len(cases) >= 20
    assert {case["kind"] for case in cases} == {
        "environment", "bug", "skill_gap", "capability_gap", "unclear_spec", "policy"
    }
    assert all(case["expected_route"] and case["expected_outcome"] for case in cases)
    assert all(case["wrong_auto_resolution"] is False for case in cases)


def test_cases_preserve_owner_gates():
    cases = run_claims.load_cases(Path(__file__).parent / "cases.json")

    for case in cases:
        if case["kind"] == "unclear_spec":
            assert case["expected_route"] == "owner"
            assert case["expected_outcome"] == "owner"
        if case["kind"] == "policy":
            assert case["expected_outcome"] == "proposed"
            assert case["auto_resolve_allowed"] is False
