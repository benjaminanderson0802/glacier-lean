"""Document conversion child process: memory cap with few malloc arenas (works on many-core machines)."""
import subprocess

import files_store


def test_conversion_child_limits_malloc_arenas_and_caps_memory(monkeypatch, tmp_path):
    seen = {}

    def fake_run(args, **kw):
        seen["env"], seen["script"] = kw.get("env") or {}, args[2]
        return subprocess.CompletedProcess(args, 0, stdout=b"text", stderr=b"")

    monkeypatch.setattr(files_store.subprocess, "run", fake_run)
    doc = tmp_path / "a.md"; doc.write_text("# a\n", encoding="utf-8")
    assert files_store._convert_in_child(doc) == "text"
    assert seen["env"].get("MALLOC_ARENA_MAX") == "2"
    assert "cap = 2 * 1024 * 1024 * 1024" in seen["script"]


def test_real_conversion_works_under_the_cap(tmp_path):
    doc = tmp_path / "meeting.md"; doc.write_text("# Meeting\n\nQuasar agenda details.\n", encoding="utf-8")
    for _ in range(3):  # flaky before the fix on many-core machines
        assert "Quasar" in files_store._convert_in_child(doc)
