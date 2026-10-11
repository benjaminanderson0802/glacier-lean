"""Card-specific regression tests for terminal claim benchmark sampling."""

import importlib.util
from pathlib import Path


def _runner():
    path = Path(__file__).with_name("run_claims.py")
    spec = importlib.util.spec_from_file_location("claims_bench_fix_runner_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _case(case_id="routed-proof"):
    return {
        "id": case_id,
        "kind": "bug",
        "summary": "specialist proof must finish",
        "evidence": "seeded failure",
        "expected_route": "debugger",
        "expected_outcome": "resolved",
        "auto_resolve_allowed": True,
        "wrong_auto_resolution": False,
    }


class SequenceAPI:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.polls = 0

    def file_claim(self, case):
        return case["id"]

    def get_claim(self, claim_id):
        self.polls += 1
        return self.snapshots[min(self.polls - 1, len(self.snapshots) - 1)]


def _claim(status, *, assigned="debugger", proof="", body=""):
    return {
        "meta": {"status": status, "assigned_to": assigned, "resolution_evidence": proof},
        "body": body,
    }


def test_routed_claim_is_polled_until_proof_backed_resolution(monkeypatch):
    runner = _runner()
    api = SequenceAPI([
        _claim("routed"),
        _claim("routed"),
        _claim("resolved", proof="run:proof-run-17", body="Fixed and proven by run proof-run-17."),
    ])
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    row = runner.run_cases(api, [_case()], timeout=1)[0]

    assert api.polls == 3
    assert row["status"] == "resolved"
    assert row["resolved_with_evidence"]


def test_routed_timeout_and_terminal_proposal_remain_unresolved(monkeypatch):
    runner = _runner()

    class Clock:
        now = 0.0

        def monotonic(self):
            return self.now

        def sleep(self, seconds):
            self.now += seconds

    clock = Clock()
    monkeypatch.setattr(runner.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(runner.time, "sleep", clock.sleep)
    running = SequenceAPI([_claim("routed")])
    stuck = runner.run_cases(running, [_case("still-running")], timeout=1)[0]

    proposal_case = _case("owner-proposal")
    proposal_case.update(expected_route="owner", expected_outcome="proposed")
    proposal = SequenceAPI([_claim("proposed", assigned="owner")])
    proposed = runner.run_cases(proposal, [proposal_case], timeout=1)[0]

    assert running.polls > 1
    assert stuck["status"] == "routed"
    assert not stuck["resolved_with_evidence"]
    assert proposal.polls == 1
    assert proposed["status"] == "proposed"
    assert proposed["escalated_when_expected"]
    assert not proposed["resolved_with_evidence"]
