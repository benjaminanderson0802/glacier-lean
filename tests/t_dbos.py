"""Smoke test: DBOS on SQLite - crash mid-workflow, restart, resume without redoing finished steps; cron schedule fires."""
import os, sys, time
from dbos import DBOS, DBOSConfig

DBOS(config=DBOSConfig(name="glacier-smoke", system_database_url="sqlite:///dbos_smoke.sqlite"))
LOG = "steps.log"

def log(s):
    with open(LOG, "a") as f: f.write(s + "\n")

@DBOS.step()
def step(i: int) -> int:
    log(f"step {i} ran")
    if i == 2 and not os.path.exists("crashed_once"):
        open("crashed_once", "w").close()
        log("CRASH")
        os._exit(1)  # simulate power loss mid-run
    return i

@DBOS.workflow()
def environment_run() -> str:
    for i in range(1, 4):
        step(i)
    log("workflow done")
    return "ok"

@DBOS.workflow()
def heartbeat(when, context) -> None:
    log("tick")

if __name__ == "__main__":
    DBOS.launch()  # on restart, DBOS recovers pending workflows automatically
    if sys.argv[1] == "start":
        DBOS.create_schedule(schedule_name="hb", workflow_fn=heartbeat, schedule="* * * * * *")
        DBOS.start_workflow(environment_run)
        time.sleep(5)
    else:
        time.sleep(4)
    DBOS.destroy()
