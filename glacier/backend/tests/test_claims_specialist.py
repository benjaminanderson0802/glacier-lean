"""A stuck flow is repaired by a specialist and proven by a re-run, with no human involved."""
import os, sys, time, textwrap
from conftest import Server, env

SPECIALIST = textwrap.dedent('''
    import os, sys
    args = sys.argv[1:]
    workdir = args[args.index("-C") + 1]; out = args[args.index("-o") + 1]
    open(os.path.join(workdir, "config.txt"), "w").write("mode=fast\\n")
    open(out, "w").write("Created the missing config.txt.")
''')


def test_stuck_flow_is_fixed_and_proven(tmp_path, monkeypatch):
    script = tmp_path / "specialist.py"; script.write_text(SPECIALIST)
    executable = script
    if os.name != "nt":
        executable = tmp_path / "spec.sh"
        executable.write_text(f"#!/bin/sh\nexec {sys.executable} {script} \"$@\"\n")
        executable.chmod(0o755)
    monkeypatch.setenv("GLACIER_SPECIALIST_BIN", str(executable))
    home = tmp_path / "home"; home.mkdir()
    s = Server(home).start()
    try:
        e = env("needs-config", [("c", "command", {"cmd": "cat config.txt"}), ("k", "check", {"expr": "exit_code == 0"}),
                                 ("n", "note", {"path": "runs/{run}.md", "template": "ok"})],
                [("c", "k", ""), ("k", "n", "yes"), ("k", "c", "no")])
        s.put("/api/environments/needs-config", e)
        first = s.wait_run(s.post("/api/environments/needs-config/run")["run_id"])
        assert first["status"] == "failed"
        deadline = time.time() + 90
        while time.time() < deadline:
            cl = s.get("/api/claims")
            if cl and cl[0]["status"] in ("resolved", "proposed"):
                break
            time.sleep(0.5)
        c = s.get(f"/api/claims/{cl[0]['id']}")
        assert c["meta"]["status"] == "resolved", c
        rerun = c["meta"]["resolution_evidence"].split(":", 1)[1]
        r = s.get(f"/api/runs/{rerun}")
        assert r["status"] == "done" and r["node_states"]["n"] == "done"
        assert "Created the missing config.txt" in c["body"]
    finally:
        s.stop()
