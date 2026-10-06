"""Glacier basics test board. Runs every foundation test and writes RESULTS.md (pass/fail + evidence).
No AI models are used. Run from the repo root:  python tests/run_all.py"""
import datetime, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
results = []

def run(cmd, cwd=HERE, timeout=300):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)

def record(name, ok, evidence):
    results.append((name, ok, evidence.strip().replace("\n", " / ")[:400]))
    print(("PASS " if ok else "FAIL ") + name)

# 1. Workflow engine: loop, human approval, resume in a new process
try:
    run(["rm", "-rf", "ckpt", "req_id"])
    c1, o1 = run([PY, "t_maf.py", "1"])
    c2, o2 = run([PY, "t_maf.py", "2"])
    ok = c1 == 0 and c2 == 0 and "IDLE_WITH_PENDING_REQUESTS" in o1 and o1.count("loop back") == 2 and "human said True" in o2
    record("Workflow engine: loop + approval pause + resume after restart", ok, o1[-300:] + " || " + o2[-200:])
except Exception as e:
    record("Workflow engine: loop + approval pause + resume after restart", False, repr(e))

# 2. Scheduler: crash mid-run, restart resumes without redoing finished steps; schedule survives restart
try:
    run(["rm", "-f", "dbos_smoke.sqlite", "dbos_smoke.sqlite-wal", "dbos_smoke.sqlite-shm", "steps.log", "crashed_once"])
    c1, o1 = run([PY, "t_dbos.py", "start"])
    lines_before = open(os.path.join(HERE, "steps.log")).read().splitlines()
    c2, o2 = run([PY, "t_dbos.py", "resume"])
    lines = open(os.path.join(HERE, "steps.log")).read().splitlines()
    after = lines[len(lines_before):]
    ok = (c1 != 0 and "CRASH" in lines_before and lines.count("step 1 ran") == 1 and lines.count("step 3 ran") == 1
          and lines.count("workflow done") == 1 and after.count("tick") >= 1)
    record("Scheduler: crash recovery + persistent schedule", ok, "log: " + ", ".join(lines))
except Exception as e:
    record("Scheduler: crash recovery + persistent schedule", False, repr(e))

# 3. Shared memory vault over MCP
c, o = run([PY, "t_memory.py"])
record("Shared memory: vault + git + search + links + undo", c == 0 and "PASS" in o, o[-400:])

# 4. Screen pieces: canvas, terminal-in-node, code editor, memory graph
ui = os.path.join(HERE, "ui")
c, o = run(["npx", "vite", "build"], cwd=ui, timeout=600)
if c == 0:
    srv = subprocess.Popen(["npx", "vite", "preview", "--port", "4173", "--host", "0.0.0.0"], cwd=ui, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import time; time.sleep(4)
        c, o = run(["node", "e2e.mjs"], cwd=ui, timeout=180)
    finally:
        srv.terminate()
    record("Screen: canvas + terminal node + editor + graph", c == 0 and "PASS" in o, o[-400:])
else:
    record("Screen: canvas + terminal node + editor + graph", False, "build failed: " + o[-300:])

passed = sum(ok for _, ok, _ in results)
with open(os.path.join(os.path.dirname(HERE), "RESULTS.md"), "w") as f:
    f.write(f"# Glacier basics test board\n\nRun: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC. Passed {passed} of {len(results)}.\n\n")
    f.write("| Test | Result | Evidence |\n| --- | --- | --- |\n")
    for n, ok, ev in results:
        f.write(f"| {n} | {'PASS' if ok else 'FAIL'} | {ev.replace('|', '/')} |\n")
print(f"\n{passed}/{len(results)} passed. See RESULTS.md")
sys.exit(0 if passed == len(results) else 1)
