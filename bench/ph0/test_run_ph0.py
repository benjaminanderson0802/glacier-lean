import run_ph0


def test_license_records_are_versioned_spdx_records():
    records = run_ph0.license_records()
    assert records["agent-framework-core"]["version"] == "1.19.0"
    assert records["agent-framework-core"]["spdx"] == "MIT"
    assert records["agent-client-protocol"]["version"] == "0.12.1"
    assert records["agent-client-protocol"]["spdx"] == "Apache-2.0"


def test_replacements_pass_only_when_their_existing_checks_pass(monkeypatch):
    monkeypatch.setattr(run_ph0, "run_replacement_tests", lambda paths: (False, "1 failed"))
    monkeypatch.setattr(run_ph0, "run_editor_replacement_check", lambda: (False, "e2e failed"))
    failed = run_ph0.replacement_rows()
    assert [row[1] for row in failed] == [False, False, False, False]

    monkeypatch.setattr(run_ph0, "run_replacement_tests", lambda paths: (True, "6 passed"))
    monkeypatch.setattr(run_ph0, "run_editor_replacement_check", lambda: (True, "editor e2e passed"))
    passed = run_ph0.replacement_rows()
    assert [row[1] for row in passed] == [True, True, True, True]
    assert "replaced by" in passed[0][2]
    assert "PR #19" in passed[1][2]
    assert "PRs #28, #52" in passed[2][2]
    assert "PR #54" in passed[3][2]
