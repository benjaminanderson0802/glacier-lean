"""Approval-gated UI change proposals applied in private Git worktrees."""
from __future__ import annotations

import os
import re
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_DIFF_CHARS = 80_000
_proposals: dict[str, dict] = {}


def validate_diff(diff: str) -> list[str]:
    if not isinstance(diff, str) or not diff.strip() or len(diff) > MAX_DIFF_CHARS:
        raise ValueError("Provide a unified diff no larger than 80,000 characters.")
    paths: set[str] = set()
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")):
            raw = line[4:].split("\t", 1)[0].strip()
            if raw == "/dev/null":
                continue
            raw = raw.removeprefix("a/").removeprefix("b/")
            normalized = Path(raw)
            if normalized.is_absolute() or ".." in normalized.parts or not raw.startswith("glacier/web/src/"):
                raise ValueError("UI changes may edit files under glacier/web/src only.")
            paths.add(raw)
    if not paths:
        raise ValueError("The diff must include a file under glacier/web/src.")
    return sorted(paths)


def _validate_spec(spec: str) -> str:
    if not isinstance(spec, str) or not re.fullmatch(r"glacier/web/e2e/[A-Za-z0-9_.-]+\.spec\.mjs", spec):
        raise ValueError("Choose a related e2e spec under glacier/web/e2e.")
    if not (ROOT / spec).is_file():
        raise ValueError("The related e2e spec does not exist in glacier/web/e2e.")
    return spec


def propose(diff: str, explanation: str, related_spec: str) -> dict:
    validate_diff(diff)
    explanation = str(explanation or "").strip()
    if not explanation or len(explanation) > 1200:
        raise ValueError("Add a plain explanation of the proposed UI change (up to 1,200 characters).")
    spec = _validate_spec(related_spec)
    proposal_id = str(uuid.uuid4())
    item = {"id": proposal_id, "kind": "ui_change", "diff": diff, "explanation": explanation,
            "related_spec": spec}
    _proposals[proposal_id] = item
    return dict(item)


def discard(proposal_id: str) -> None:
    _proposals.pop(proposal_id, None)


def _command(args: list[str], cwd: Path, timeout: int = 900) -> dict:
    try:
        result = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
        return {"passed": result.returncode == 0, "exit_code": result.returncode,
                "output": (result.stdout + result.stderr)[-5000:]}
    except (OSError, subprocess.SubprocessError) as error:
        return {"passed": False, "exit_code": None, "output": str(error)}


def _run_checks(worktree: Path, related_spec: str) -> dict:
    web = worktree / "glacier/web"
    results = {
        "tsc": _command(["npx", "tsc", "-b"], web),
        "theme lint": _command(["node", "e2e/theme_lint.mjs"], web),
        "build": _command(["npm", "run", "build"], web),
    }
    results["e2e"] = (_command(["node", related_spec.removeprefix("glacier/web/")], web)
                      if results["build"]["passed"] else
                      {"passed": False, "exit_code": None, "output": "Skipped because the web build failed."})
    return {"passed": all(result["passed"] for result in results.values()), "results": results}


def apply(proposal_id: str, proposal: dict | None = None) -> dict:
    proposal = proposal or _proposals.get(proposal_id)
    if proposal is None:
        raise KeyError("UI change proposal not found")
    paths = validate_diff(proposal["diff"])
    related_spec = _validate_spec(proposal["related_spec"])
    branch = f"assistant/ui-change/{proposal_id}"
    worktree_root = Path(os.environ.get("GLACIER_HOME", str(Path.home() / ".glacier")))
    worktree = worktree_root / "worktrees" / "ui-changes" / proposal_id
    worktree.parent.mkdir(parents=True, exist_ok=True)
    added = _command(["git", "-C", str(ROOT), "worktree", "add", "-b", branch, str(worktree), "HEAD"], ROOT)
    if not added["passed"]:
        raise RuntimeError("Could not create the isolated UI change worktree: " + added["output"][-1000:])
    if not worktree.is_dir():
        raise RuntimeError("Could not create the isolated UI change worktree.")
    result = subprocess.run(["git", "apply", "--check", "-"], cwd=str(worktree), input=proposal["diff"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        return {"applied": False, "branch": branch, "worktree": str(worktree),
                "checks": [], "passed": False, "error": (result.stderr or result.stdout)[-2000:]}
    result = subprocess.run(["git", "apply", "-"], cwd=str(worktree), input=proposal["diff"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        return {"applied": False, "branch": branch, "worktree": str(worktree),
                "checks": [], "passed": False, "error": (result.stderr or result.stdout)[-2000:]}
    # A worktree can use the already-installed, pinned dependencies without modifying the live checkout.
    source_modules = ROOT / "glacier/web/node_modules"
    target_modules = worktree / "glacier/web/node_modules"
    if source_modules.exists() and not target_modules.exists():
        try:
            target_modules.symlink_to(source_modules.resolve(), target_is_directory=True)
        except OSError:
            pass
    added_files = _command(["git", "add", "--", *paths], worktree)
    if not added_files["passed"]:
        return {"applied": True, "branch": branch, "worktree": str(worktree), "checks": [], "passed": False,
                "error": "Could not stage the UI diff: " + added_files["output"][-1000:]}
    commit = _command(["git", "-c", "user.name=Glacier Assistant", "-c", "user.email=assistant@glacier.local",
                       "commit", "-m", f"Propose Glacier UI change {proposal_id}"], worktree)
    if not commit["passed"]:
        return {"applied": True, "branch": branch, "worktree": str(worktree), "checks": [], "passed": False,
                "error": "Could not commit the UI diff: " + commit["output"][-1000:]}
    checks = _run_checks(worktree, related_spec)
    _proposals.pop(proposal_id, None)
    return {"applied": True, "branch": branch, "worktree": str(worktree), "checks": list(checks["results"]),
            "check_results": checks["results"], "passed": checks["passed"], "changed_files": paths}
