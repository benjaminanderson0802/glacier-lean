"""Focused PH5 supervisor evidence regression from CLM-2026-10-11-E-PH5-LIVE-REVIEW."""
import sys

import pytest

import teams


EXPECTED = b"Glacier PH5 verified\n"


def _plan():
    return {
        "vision": {"goal": "Create the exact result file", "done": ["result.txt has exact bytes"]},
        "spec": {"acceptance": []},
        "features": [],
        "team": {
            "worker_mode": "parallel",
            "parallel_limit": 1,
            "supervisor": "lead",
            "roles": [
                {"id": "builder", "charter": "Write result.txt exactly"},
                {"id": "lead", "charter": "Review the handover against its evidence"},
            ],
        },
        "tasks": [],
    }


def _task():
    check = {
        "kind": "command",
        "cmd": f'{sys.executable} -c "from pathlib import Path; assert Path(\'result.txt\').read_bytes() == bytes.fromhex(\'{EXPECTED.hex()}\')"',
    }
    return {
        "id": "write",
        "title": "Create exact result file",
        "role": "builder",
        "depends_on": [],
        "acceptance": [check],
    }


def _run_task(tmp_path, monkeypatch, *, reviewer_choice, file_bytes=EXPECTED):
    import decider

    plan = _plan()
    task = _task()
    reviewer_calls = []

    def worker(_context, workspace, _task):
        if file_bytes is not None:
            from pathlib import Path
            (Path(workspace) / "result.txt").write_bytes(file_bytes)
        return {"output": "Created result.txt.", "exit_code": 0}

    def decide(question, options, context="", engine="auto", model=""):
        reviewer_calls.append({"question": question, "context": context, "engine": engine})
        return {"choice": reviewer_choice, "engine": "separate-reviewer-fixture"}

    monkeypatch.setattr(teams, "_worker", worker)
    monkeypatch.setattr(teams, "_relevant_memory", lambda *_: [])
    monkeypatch.setattr(decider, "decide", decide)
    outcome = teams.execute_task(
        "team-fixture", "write", plan, task, str(tmp_path),
        {"tasks": {"write": {"approved": True}}},
    )
    return outcome, reviewer_calls, task


def test_C_PH5_SUPERVISOR_accepts_exact_byte_check_with_separate_reviewer(tmp_path, monkeypatch):
    outcome, reviewer_calls, task = _run_task(tmp_path, monkeypatch, reviewer_choice="pass")

    assert outcome["checks"]["passed"] is True
    assert outcome["status"] == "done"
    assert len(reviewer_calls) == 1
    assert "Independent check results" in reviewer_calls[0]["context"]
    assert "exited 0" in reviewer_calls[0]["context"]
    assert task["acceptance"][0]["kind"] == "command"


def test_C_PH5_SUPERVISOR_rejects_unreasoned_contradiction_of_exact_byte_pass(tmp_path, monkeypatch):
    outcome, reviewer_calls, _ = _run_task(tmp_path, monkeypatch, reviewer_choice="fail")

    assert outcome["checks"]["passed"] is True
    assert outcome["status"] != "done"
    assert len(reviewer_calls) == 1
    # A bare pass/fail choice is not a reason to contradict the exact-byte evidence.
    review_evidence = outcome["review"].get("evidence", "")
    assert "reason" in review_evidence.lower() or "because" in review_evidence.lower()


@pytest.mark.parametrize("file_bytes", [None, b"Glacier PH5 verified\nextra"])
def test_C_PH5_SUPERVISOR_blocks_missing_or_failing_exact_byte_evidence(
    tmp_path, monkeypatch, file_bytes
):
    outcome, reviewer_calls, _ = _run_task(
        tmp_path, monkeypatch, reviewer_choice="pass", file_bytes=file_bytes
    )

    assert outcome["checks"]["passed"] is False
    assert outcome["status"] != "done"
    assert len(reviewer_calls) == 1
    assert '"passed": false' in reviewer_calls[0]["context"].lower()
