import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import store


def test_acceptance_evidence_is_redacted_before_storage(tmp_path, monkeypatch):
    import secrets_store

    store.init(str(tmp_path / "glacier.sqlite"))
    monkeypatch.setattr(secrets_store, "redact", lambda value: value.replace("private-value", "[secret key]"))

    store.record_check("audit-run", 0, "command", False, "check output: private-value")

    evidence = store.checks_of("audit-run")[0]["evidence"]
    assert evidence == "check output: [secret key]"
