import claims_specialist as cs


def test_no_acceptance_means_finished_rerun_is_the_proof():
    assert cs.proof_verified("done", [], []) is None


def test_missing_check_results_are_never_a_pass():
    assert cs.proof_verified("done", [{"kind": "command"}], []) is False
    assert cs.proof_verified("done", [{"kind": "command"}, {"kind": "schema"}], [{"passed": True}]) is False


def test_all_checks_recorded_and_passed_is_verified():
    assert cs.proof_verified("done", [{"kind": "command"}], [{"passed": True}]) is True
    assert cs.proof_verified("failed", [{"kind": "command"}], [{"passed": True}]) is False
    assert cs.proof_verified("done", [{"kind": "command"}], [{"passed": False}]) is False
