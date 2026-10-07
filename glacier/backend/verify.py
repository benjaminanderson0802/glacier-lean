"""Acceptance checks, run by the verifier outside the worker's control (docs/contracts/VERIFICATION.md, rule I-04).
Each check runs on a fresh copy of the flow's workspace; files the check owns ("files") are restored from the saved
flow, so a worker that edits or weakens them changes nothing."""
import json, os, shutil, subprocess, tempfile
import decider
import shell_commands

KINDS = ("command", "schema", "rubric", "human")
CHECK_TIMEOUT = 600


def validate(acceptance) -> None:
    if acceptance is None:
        return
    if not isinstance(acceptance, list):
        raise ValueError("acceptance must be a list of checks")
    for i, c in enumerate(acceptance):
        if not isinstance(c, dict) or c.get("kind") not in KINDS:
            raise ValueError(f"check {i + 1}: kind must be one of {', '.join(KINDS)}")
        need = {"command": "cmd", "schema": "schema", "rubric": "rubric", "human": "question"}[c["kind"]]
        if not c.get(need):
            raise ValueError(f"check {i + 1} ({c['kind']}) needs '{need}'")


def workspace(home: str, env_id: str, check: dict, ws: str = "") -> str:
    return check.get("cwd") or ws or os.path.join(home, "workspaces", env_id)


def run_check(home: str, env_id: str, check: dict, last_output: str, run_ws: str = "") -> dict:
    kind = check["kind"]
    ws = workspace(home, env_id, check, run_ws)
    if kind == "rubric":
        q = ("You are an independent reviewer. Judge ONLY whether the work below meets the criteria. "
             f"Criteria: {check['rubric']}\nAnswer pass or fail.")
        d = decider.decide(q, ["pass", "fail"], last_output or "(no output)", check.get("engine") or "auto", check.get("model") or "")
        return {"passed": d["choice"] == "pass", "evidence": f"reviewer ({d['engine']}) said {d['choice']}"}
    with tempfile.TemporaryDirectory(prefix="glacier-check-") as tmp:
        copy = os.path.join(tmp, "work")
        if os.path.isdir(ws):
            shutil.copytree(ws, copy, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        else:
            os.makedirs(copy)
        notes = []
        for rel, content in (check.get("files") or {}).items():
            target = os.path.normpath(os.path.join(copy, rel))
            if not target.startswith(copy + os.sep):
                return {"passed": False, "evidence": f"check file {rel!r} is outside the workspace"}
            original = os.path.join(ws, rel)
            if os.path.exists(original):
                with open(original, errors="replace") as f:
                    if f.read() != content:
                        notes.append(f"the worker changed {rel} (a protected check file)")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w") as f:
                f.write(content)
        if notes:  # rule I-04: touching the check that judges you is never accepted, even if the work is right
            return {"passed": False, "evidence": "\n".join(notes + ["not accepted: the worker changed a protected check file"])}
        if kind == "command":
            try:
                command, shell, warning = shell_commands.command_invocation(check["cmd"])
                p = subprocess.run(command, shell=shell, cwd=copy, capture_output=True, text=True, timeout=CHECK_TIMEOUT,
                                   stdin=subprocess.DEVNULL)
                ok, out = p.returncode == 0, (warning + p.stdout + p.stderr)[-1500:]
            except subprocess.TimeoutExpired:
                ok, out = False, f"check timed out after {CHECK_TIMEOUT}s"
            ev = f"`{check['cmd']}` exited {'0' if ok else 'non-zero'}" + (f"\n{out}" if out.strip() else "")
            return {"passed": ok, "evidence": "\n".join(notes + [ev])}
        if kind == "schema":
            path = os.path.join(copy, check.get("file") or "")
            try:
                with open(path) as f:
                    data = json.load(f)
            except (OSError, ValueError) as e:
                return {"passed": False, "evidence": "\n".join(notes + [f"could not read {check.get('file')}: {e}"])}
            import jsonschema
            try:
                jsonschema.validate(data, check["schema"])
                return {"passed": True, "evidence": "\n".join(notes + [f"{check.get('file')} matches the schema"])}
            except jsonschema.ValidationError as e:
                return {"passed": False, "evidence": "\n".join(notes + [f"{check.get('file')}: {e.message}"])}
    raise ValueError(f"unsupported check kind {kind!r}")
