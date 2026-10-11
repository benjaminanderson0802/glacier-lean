"""Independent regression checks for terminal, proof-backed claim outcomes.

Acceptance contract:
* A specialist-routed claim is polled until its proof run finishes and the claim
  reaches a terminal outcome; the routed intermediate state is never scored.
* A terminal ``resolved`` status counts only with linked proof evidence.
* ``proposed`` is terminal but unresolved, and a still-routed claim at timeout
  remains unresolved.

These checks exercise the public benchmark runner entry point without editing
its implementation or its existing judging tests.
"""

import importlib.util
from pathlib import Path


def _runner():
    path = Path(__file__).with_name("run_claims.py")
    spec = importlib.util.spec_from_file_location("claims_bench_terminal_outcome_test", path)
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


def test_routed_claim_is_not_sampled_until_specialist_proof_is_terminal(monkeypatch):
    runner = _runner()
    # The specialist workflow remains active in the first two observations.
    api = SequenceAPI([
        _claim("routed"),
        _claim("routed"),
        _claim("resolved", proof="run:proof-run-17", body="Fixed and proven by run proof-run-17."),
    ])
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    row = runner.run_cases(api, [_case()], timeout=1)[0]

    assert api.polls == 3, "benchmark sampled the routed claim before specialist proof completed"
    assert row["status"] == "resolved"
    assert row["resolved_with_evidence"]


def test_terminal_status_without_linked_proof_does_not_count_as_resolved():
    runner = _runner()
    api = SequenceAPI([_claim("resolved", body="Specialist says it is fixed.")])

    row = runner.run_cases(api, [_case()], timeout=0)[0]

    assert row["status"] == "resolved"
    assert not row["resolved_with_evidence"]


def test_proposed_is_terminal_but_not_a_resolved_sample():
    runner = _runner()
    case = _case("owner-proposal")
    case.update(expected_route="owner", expected_outcome="proposed")
    api = SequenceAPI([_claim("proposed", assigned="owner", body="Owner decision required.")])

    row = runner.run_cases(api, [case], timeout=0)[0]

    assert api.polls == 1
    assert row["status"] == "proposed"
    assert not row["resolved_with_evidence"]
    assert row["escalated_when_expected"]


def test_still_running_routed_claim_is_polled_through_timeout_and_stays_unresolved(monkeypatch):
    runner = _runner()
    api = SequenceAPI([_claim("routed")])

    class Clock:
        now = 0.0

        def monotonic(self):
            return self.now

        def sleep(self, seconds):
            self.now += seconds

    clock = Clock()
    monkeypatch.setattr(runner.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(runner.time, "sleep", clock.sleep)

    row = runner.run_cases(api, [_case("still-running")], timeout=1)[0]

    assert api.polls > 1, "benchmark stopped polling while the specialist proof was still running"
    assert row["status"] == "routed"
    assert not row["resolved_with_evidence"]
