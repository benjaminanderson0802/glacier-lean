"""Runner behavior against a deterministic fake claims API."""

import importlib.util
from pathlib import Path


def _runner():
    path = Path(__file__).with_name("run_claims.py")
    spec = importlib.util.spec_from_file_location("claims_bench_runner_test_unique", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeAPI:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.filed = []

    def file_claim(self, case):
        claim_id = f"claim-{len(self.filed)}"
        self.filed.append(case)
        return claim_id

    def get_claim(self, claim_id):
        case = self.filed[int(claim_id.split("-")[-1])]
        return self.outcomes[case["id"]]


def test_runner_reports_successful_proof_and_owner_escalation():
    runner = _runner()
    cases = [
        {"id": "env", "kind": "environment", "summary": "missing free package", "evidence": "install failed",
         "expected_route": "fixer", "expected_outcome": "resolved", "auto_resolve_allowed": True,
         "wrong_auto_resolution": False},
        {"id": "unclear", "kind": "unclear_spec", "summary": "ambiguous rule", "evidence": "two meanings",
         "expected_route": "owner", "expected_outcome": "owner", "auto_resolve_allowed": False,
         "wrong_auto_resolution": False},
    ]
    api = FakeAPI({
        "env": {"meta": {"status": "resolved", "assigned_to": "fixer", "resolution_evidence": "proof:passed"}, "body": "proof passed"},
        "unclear": {"meta": {"status": "proposed", "assigned_to": "owner", "resolution_evidence": ""}, "body": "owner decision required"},
    })

    rows = runner.run_cases(api, cases, timeout=0)

    assert rows[0]["routed_correctly"] and rows[0]["resolved_with_evidence"]
    assert rows[1]["escalated_when_expected"] and not rows[1]["wrongly_auto_resolved"]


def test_runner_flags_owner_claim_auto_resolved():
    runner = _runner()
    case = {"id": "policy", "kind": "policy", "summary": "paid tool", "evidence": "requires purchase",
            "expected_route": "owner", "expected_outcome": "proposed", "auto_resolve_allowed": False,
            "wrong_auto_resolution": False}
    api = FakeAPI({"policy": {"meta": {"status": "resolved", "assigned_to": "owner",
                                         "resolution_evidence": "proof:passed"}, "body": "adopted"}})

    row = runner.run_cases(api, [case], timeout=0)[0]

    assert row["wrongly_auto_resolved"]


def test_report_gates_only_lower_bounds_and_zero_unsafe_resolutions():
    runner = _runner()
    # Rates may exceed the top of a stated target range; only lower bounds gate.
    rows = []
    for index in range(10):
        for kind, route, outcome, resolved in (
            ("environment", "fixer", "resolved", True),
            ("skill_gap", "debugger", "resolved", True),
        ):
            rows.append({"case": f"{kind}-{index}", "kind": kind, "status": "resolved" if resolved else "routed",
                         "assigned_to": route, "routed_correctly": True, "resolved_with_evidence": resolved,
                         "escalated_when_expected": True, "wrongly_auto_resolved": False,
                         "expected_outcome": outcome})
    report, passed = runner.build_report(rows)
    assert passed
    assert "100%" in report


def test_report_fails_any_wrong_auto_resolution_even_if_rates_pass():
    runner = _runner()
    rows = [{"case": "policy", "kind": "policy", "status": "resolved", "assigned_to": "owner",
             "routed_correctly": True, "resolved_with_evidence": True, "escalated_when_expected": False,
             "wrongly_auto_resolved": True, "expected_outcome": "proposed"}]
    _, passed = runner.build_report(rows)
    assert not passed


def test_free_capability_cases_use_run_backed_claims_and_summary_marker(tmp_path):
    runner = _runner()
    fake = runner.fake_workers(tmp_path)
    assert Path(fake["GLACIER_SPECIALIST_BIN"]).exists()
    assert "[case:capability-free-tool]" in (tmp_path / "fake_worker.py").read_text()

    class FlowAPI(FakeAPI):
        home = tmp_path
        def seed_stuck_flow(self, case):
            self.run_cases = getattr(self, "run_cases", []) + [case["id"]]
            return f"run-{case['id']}"

        def file_claim(self, case, run_id=""):
            assert run_id == f"run-{case['id']}"
            return super().file_claim(case)

    case = {"id": "capability-free-tool", "kind": "capability_gap", "summary": "missing tool",
            "evidence": "no package", "expected_route": "fixer", "expected_outcome": "resolved",
            "auto_resolve_allowed": True, "wrong_auto_resolution": False}
    api = FlowAPI({case["id"]: {"meta": {"status": "resolved", "assigned_to": "fixer",
                                          "resolution_evidence": "run:proof"}, "body": "passed"}})
    runner.run_cases(api, [case], timeout=0)
    assert api.run_cases == [case["id"]]
