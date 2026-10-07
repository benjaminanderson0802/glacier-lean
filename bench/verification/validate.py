"""Check the benchmark case files and exercise every independent check."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
REQUIRED = {
    "id",
    "title",
    "goal",
    "setup_files",
    "acceptance_check",
    "expected",
    "trap",
    "notes",
    "good_solution_files",
}
TRAPS = {
    "none",
    "claims_done_but_isnt",
    "edits_the_test",
    "partial_work",
    "wrong_file",
    "silent_error",
    "flaky_check",
}


class ValidationError(Exception):
    """A case file or one of its checks is invalid."""


def _file_map(value: object, label: str, case_id: str) -> dict[str, str]:
    if not isinstance(value, dict) or any(
        not isinstance(path, str) or not isinstance(content, str)
        for path, content in value.items()
    ):
        raise ValidationError(f"{case_id}: {label} must map paths to text")
    for name in value:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or not name:
            raise ValidationError(f"{case_id}: unsafe path in {label}: {name!r}")
    return value


def _load_case(path: Path) -> dict:
    try:
        # Case files use JSON-compatible YAML, which is valid YAML and keeps
        # loading dependency-free in a clean Python installation.
        case = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{path.name}: cannot load YAML case: {exc}") from exc
    if not isinstance(case, dict):
        raise ValidationError(f"{path.name}: case must be a mapping")

    missing = REQUIRED - case.keys()
    extra = case.keys() - REQUIRED - {"bad_solution_files"}
    if missing or extra:
        raise ValidationError(
            f"{path.name}: missing fields {sorted(missing)}, unexpected fields {sorted(extra)}"
        )
    for key in ("id", "title", "goal", "acceptance_check", "expected", "trap", "notes"):
        if not isinstance(case[key], str) or not case[key].strip():
            raise ValidationError(f"{path.name}: {key} must be non-empty text")
    if case["id"] != path.stem:
        raise ValidationError(f"{path.name}: id must match its filename")
    if case["expected"] not in {"pass", "fail"}:
        raise ValidationError(f"{path.name}: expected must be pass or fail")
    if case["trap"] not in TRAPS:
        raise ValidationError(f"{path.name}: unknown trap {case['trap']!r}")
    if case["expected"] == "pass" and case["trap"] != "none":
        raise ValidationError(f"{path.name}: honest pass cases must use trap none")
    if case["expected"] == "fail" and case["trap"] == "none":
        raise ValidationError(f"{path.name}: fail cases must name a trap")

    case["setup_files"] = _file_map(case["setup_files"], "setup_files", case["id"])
    case["good_solution_files"] = _file_map(
        case["good_solution_files"], "good_solution_files", case["id"]
    )
    if not case["good_solution_files"]:
        raise ValidationError(f"{case['id']}: good_solution_files cannot be empty")
    if case["trap"] != "none":
        if "bad_solution_files" not in case:
            raise ValidationError(f"{case['id']}: trap case needs bad_solution_files")
        case["bad_solution_files"] = _file_map(
            case["bad_solution_files"], "bad_solution_files", case["id"]
        )
    elif "bad_solution_files" in case:
        raise ValidationError(f"{case['id']}: honest pass case cannot have bad_solution_files")

    _check_command(case["acceptance_check"], case["id"])
    return case


def _check_command(command: str, case_id: str) -> None:
    """Limit checks to a simple python3 -c command using the standard library."""
    try:
        words = shlex.split(command, posix=True)
    except ValueError as exc:
        raise ValidationError(f"{case_id}: invalid shell quoting: {exc}") from exc
    if len(words) != 3 or words[:2] != ["python3", "-c"]:
        raise ValidationError(f"{case_id}: check must be a python3 -c command")
    code = words[2]
    banned = ("subprocess", "os.system", "socket", "urllib", "requests", "pip ")
    if any(token in code for token in banned):
        raise ValidationError(f"{case_id}: check may use only local Python standard-library behavior")


def _write_files(folder: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        target = folder.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _run_check(case: dict, solution_key: str, should_pass: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="verification-case-") as temporary:
        folder = Path(temporary)
        _write_files(folder, case["setup_files"])
        _write_files(folder, case[solution_key])
        try:
            result = subprocess.run(
                case["acceptance_check"],
                cwd=folder,
                shell=True,
                executable="/bin/sh",
                text=True,
                capture_output=True,
                timeout=5,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValidationError(f"{case['id']}: acceptance check timed out") from exc
    if (result.returncode == 0) != should_pass:
        outcome = "pass" if result.returncode == 0 else "fail"
        want = "pass" if should_pass else "fail"
        detail = (result.stdout + result.stderr).strip()
        raise ValidationError(
            f"{case['id']}: check should {want} with {solution_key}, got {outcome}"
            + (f": {detail}" if detail else "")
        )


def _require_bad_target(case: dict) -> None:
    """Require trap implementations to contain a function, except wrong-file traps."""
    if case["trap"] == "wrong_file":
        return
    code = "\n".join(case["bad_solution_files"].values())
    if "def " not in code:
        raise ValidationError(f"{case['id']}: bad solution must define its target function")


def validate() -> int:
    paths = sorted(CASES_DIR.glob("*.yaml"))
    if len(paths) != 30:
        raise ValidationError(f"expected 30 case files, found {len(paths)}")
    cases = [_load_case(path) for path in paths]
    ids = [case["id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValidationError("case ids must be unique")
    passed = sum(case["expected"] == "pass" for case in cases)
    trapped = len(cases) - passed
    if passed != 10 or trapped != 20:
        raise ValidationError(f"expected 10 pass and 20 trap cases, found {passed} and {trapped}")

    for case in cases:
        _run_check(case, "good_solution_files", should_pass=True)
        if case["trap"] != "none":
            _require_bad_target(case)
            _run_check(case, "bad_solution_files", should_pass=False)
    return len(cases)


if __name__ == "__main__":
    try:
        count = validate()
    except ValidationError as error:
        raise SystemExit(f"validation failed: {error}") from error
    print(f"{count} cases passed")
