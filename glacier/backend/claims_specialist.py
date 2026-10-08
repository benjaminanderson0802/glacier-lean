"""Specialists work routed claims, then the stuck flow is re-run to prove the fix (roadmap: specialist routing and
parked-task resume). A claim is resolved only by evidence: a new run of the same flow that finishes (and is verified,
if the flow has checks). Otherwise it goes to the owner. Model policy: specialists use the sandbox Codex default model
in a fresh context (no memory of the stuck worker's attempts beyond the claim text)."""
import os, subprocess, tempfile, time
from dbos import DBOS, SetWorkflowID
import claims, store, vault, workspaces
import shell_commands

SPECIALIST_TIMEOUT = 30 * 60
WORKABLE = ("fixer", "debugger")


def _prompt(meta: dict, body: str) -> str:
    role = meta.get("assigned_to")
    return (f"You are Glacier's {role}. A flow step got stuck. Fix the cause in this folder (the flow's workspace) so the "
            "flow can succeed. Rules: do not edit or weaken any test or check; make the smallest change; explain what you "
            "changed in one short paragraph.\n\nClaim: " + meta.get("summary", "") + "\n\n" + body[:6000])


def run_specialist(workdir: str, prompt: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.txt")
        args = shell_commands.executable_invocation(os.environ.get("GLACIER_SPECIALIST_BIN") or os.environ.get("CODEX_BIN", "codex"), "exec", "--json",
                "--skip-git-repo-check", "-s", os.environ.get("GLACIER_CODEX_SANDBOX") or "workspace-write", "-C", workdir,
                "-o", out, "--", prompt)
        try:
            p = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=SPECIALIST_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 1, f"specialist could not run: {e}"
        msg = open(out).read().strip() if os.path.exists(out) else (p.stdout + p.stderr)[-800:]
        return p.returncode, msg


def _append(cid: str, text: str, **updates) -> None:
    c = claims.get_claim(cid)
    meta, body = c["meta"], c["body"]
    meta.update(updated=claims._now(), **updates)
    vault.write_note(claims._path(cid), claims._render(meta, body.rstrip() + "\n" + text.strip() + "\n"), agent="glacier-specialist")
    store.broadcaster.publish({"type": "claim", "id": cid, "status": meta.get("status")})


def _append_resolution(cid: str, text: str, **updates) -> None:
    c = claims.get_claim(cid)
    meta, body = c["meta"], c["body"]
    meta.update(updated=claims._now(), **updates)
    body = claims.append_resolution(body, text)
    vault.write_note(claims._path(cid), claims._render(meta, body), agent="glacier-specialist")
    store.broadcaster.publish({"type": "claim", "id": cid, "status": meta.get("status")})


@DBOS.step()
def specialist_attempt(cid: str) -> dict:
    c = claims.get_claim(cid)
    meta = c["meta"]
    run = store.get_run(meta.get("run_id") or "") if meta.get("run_id") else None
    if not run:
        return {"ok": False, "note": "the claim has no run to repair"}
    home = os.path.abspath(os.environ.get("GLACIER_HOME", "data"))
    ws = workspaces.base(home, run["env_id"])
    os.makedirs(ws, exist_ok=True)
    code, msg = run_specialist(ws, _prompt(meta, c["body"]))
    _append(cid, f"\n## Specialist attempt ({meta.get('assigned_to')})\nexit {code}\n{msg[-2000:]}", status="researching")
    return {"ok": code == 0, "env_id": run["env_id"], "note": msg[-300:]}


@DBOS.step(retries_allowed=True, max_attempts=3)
def create_rerun(env_id: str, rerun_id: str, cid: str) -> None:
    import runner
    graph = runner.load_env(env_id)
    graph["_rerun_of"] = cid
    store.create_run(rerun_id, env_id, graph)


def proof_verified(status: str, acceptance: list, checks: list):
    """None when the flow has no acceptance checks (then a finished re-run is the proof); otherwise True only if the
    re-run finished AND every acceptance check was actually recorded AND passed (a missing check is never a pass)."""
    if not acceptance:
        return None
    return status == "done" and len(checks) >= len(acceptance) and all(c["passed"] for c in checks)


@DBOS.step(retries_allowed=True, max_attempts=3)
def close_claim(cid: str, rerun_id: str, status: str, verified) -> dict:
    proven = status == "done" and verified is not False
    if proven:
        _append_resolution(cid, f"Fixed and proven: re-run {rerun_id} finished" + (" and passed its checks." if verified else "."),
                status="resolved", resolution=f"fixed; proven by run {rerun_id}", resolution_evidence=f"run:{rerun_id}")
        return {"status": "resolved"}
    _append(cid, f"\n## Escalated\nThe re-run {rerun_id} still ended {status}. This needs your decision.",
            status="proposed", assigned_to="owner")
    return {"status": "proposed"}


@DBOS.workflow()
def work_claim(cid: str) -> dict:
    a = specialist_attempt(cid)
    if not a.get("env_id"):
        return close_claim(cid, "", "failed", False)
    rerun_id = f"{cid[-6:]}{DBOS.workflow_id[-6:]}"[-12:]
    create_rerun(a["env_id"], rerun_id, cid)
    import runner
    with SetWorkflowID(rerun_id):
        status = DBOS.start_workflow(runner.run_environment, a["env_id"], rerun_id).get_result()
    acceptance = (store.graph_of(rerun_id).get("acceptance") or [])
    checks = store.checks_of(rerun_id)
    verified = proof_verified(status, acceptance, checks)
    return close_claim(cid, rerun_id, status, verified)


def maybe_start(cid: str, assigned_to: str) -> None:
    if assigned_to in WORKABLE and os.environ.get("GLACIER_AUTO_FIX", "1") == "1":
        DBOS.start_workflow(work_claim, cid)
