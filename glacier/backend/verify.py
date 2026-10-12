"""Acceptance checks, run by the verifier outside the worker's control (docs/contracts/VERIFICATION.md, rule I-04).
Each check runs on a fresh copy of the flow's workspace; files the check owns ("files") are restored from the saved
flow, so a worker that edits or weakens them changes nothing."""
import hashlib, json, os, shutil, stat, subprocess, tempfile
from pathlib import PureWindowsPath
import decider
import shell_commands

KINDS = ("command", "schema", "rubric", "human")
CHECK_TIMEOUT = 600


def _check_file_parts(rel: str) -> list[str]:
    # Saved flows are portable: reject Windows traversal/drives on POSIX too.
    if not isinstance(rel, str) or not rel or "\x00" in rel:
        raise ValueError("check file needs a relative path")
    path = PureWindowsPath(rel)
    parts = rel.replace("\\", "/").split("/")
    if path.drive or path.root or any(p in ("", ".", "..") or ":" in p for p in parts):
        raise ValueError(f"check file {rel!r} is outside the workspace or has an invalid path")
    return parts


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
        files = c.get("files", {})
        if not isinstance(files, dict):
            raise ValueError(f"check {i + 1}: files must map relative paths to text")
        for rel, content in files.items():
            _check_file_parts(rel)
            if not isinstance(content, str):
                raise ValueError(f"check file {rel!r} must contain text")


def workspace(home: str, env_id: str, check: dict, ws: str = "") -> str:
    return check.get("cwd") or ws or os.path.join(home, "workspaces", env_id)


def _protected_target(root: str, rel: str) -> str:
    """Inspect the private copy without following worker-controlled links."""
    parts = _check_file_parts(rel)
    target = root
    for i, part in enumerate(parts):
        target = os.path.join(target, part)
        try:
            info = os.lstat(target)
        except FileNotFoundError:
            continue  # checks supplied only in the saved flow need not exist yet
        # Windows junctions/reparse points must not redirect restoration either.
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"the worker changed {rel} (a protected check path is a link)")
        expected = stat.S_ISREG if i == len(parts) - 1 else stat.S_ISDIR
        if not expected(info.st_mode):
            raise ValueError(f"the worker changed {rel} (a protected check path has the wrong file type)")
    return target


def snapshot_protected_files(home: str, env_id: str, acceptance: list, run_ws: str = "") -> list[dict]:
    """Capture protected-file provenance before any workflow node can edit its workspace."""
    snapshots = []
    for check in acceptance:
        root = workspace(home, env_id, check, run_ws)
        files = {}
        for rel in (check.get("files") or {}):
            try:
                target = _protected_target(root, rel)
                try:
                    with open(target, "rb") as stream:
                        files[rel] = hashlib.sha256(stream.read()).hexdigest()
                except FileNotFoundError:
                    files[rel] = None
            except (OSError, ValueError) as exc:
                files[rel] = {"error": str(exc)}
        snapshots.append(files)
    return snapshots


def run_check(home: str, env_id: str, check: dict, last_output: str, run_ws: str = "",
              protected_snapshot: dict | None = None) -> dict:
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
        notes, targets = [], []
        for rel, content in (check.get("files") or {}).items():
            try:
                target = _protected_target(copy, rel)
                if protected_snapshot is not None:
                    baseline = protected_snapshot.get(rel)
                    if isinstance(baseline, dict) and baseline.get("error"):
                        notes.append(f"the protected check {rel} was unsafe before the run: {baseline['error']}")
                    elif baseline is None and os.path.lexists(target):
                        notes.append(f"the worker created protected check file {rel} during the run")
                    elif baseline is not None:
                        try:
                            with open(target, "rb") as stream:
                                current = hashlib.sha256(stream.read()).hexdigest()
                        except FileNotFoundError:
                            notes.append(f"the worker deleted protected check file {rel} during the run")
                        else:
                            if current != baseline:
                                notes.append(f"the worker changed protected check file {rel} during the run")
                if os.path.exists(target):
                    with open(target, encoding="utf-8") as f:
                        if f.read() != content:
                            notes.append(f"the worker changed {rel} (a protected check file)")
                targets.append((target, content))
            except (OSError, ValueError) as e:
                notes.append(str(e))
        if notes:  # rule I-04: touching the check that judges you is never accepted, even if the work is right
            return {"passed": False, "evidence": "\n".join(notes + ["not accepted: the worker changed a protected check file"])}
        # Do not write anything until every protected path and existing file is checked.
        for target, content in targets:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
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
