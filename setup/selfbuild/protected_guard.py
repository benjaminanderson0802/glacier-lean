#!/usr/bin/env python3
"""Compare protected files in a worker checkout with the main checkout."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


PROTECTED_GLOBS = (
    "glacier/backend/tests/**", "glacier/backend/tests/conftest.py", "conftest.py",
    "setup/health_check.py", "bench/**", "verify.py", "glacier/backend/verify.py",
    "flows/self/**",
)
HUMAN_GLOBS = ("NORTHSTAR.yaml", "glacier/contract/**", "docs/contracts/**", "verify.py", "glacier/backend/verify.py")


def files(root: Path, patterns: tuple[str, ...]) -> dict[str, str]:
    result = {}
    for pattern in patterns:
        glob = pattern.rstrip("*") if pattern.endswith("/**") else pattern
        for path in root.glob(glob):
            if path.is_file():
                result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.is_dir():
                for item in path.rglob("*"):
                    if item.is_file():
                        result[item.relative_to(root).as_posix()] = hashlib.sha256(item.read_bytes()).hexdigest()
    return result


def check(repo: Path, baseline_root: Path) -> int:
    """0 = fine; 1 = an existing protected check was modified or deleted (I-04); 2 = needs owner approval.

    Adding NEW protected files (new tests) is allowed: only files present in the baseline are compared.
    Any difference in owner-only files (NORTHSTAR.yaml, contracts, verify.py) stops for the owner.
    """
    expected, actual = files(baseline_root, PROTECTED_GLOBS), files(repo, PROTECTED_GLOBS)
    changed = sorted(path for path, digest in expected.items() if actual.get(path) != digest)
    base_human, run_human = files(baseline_root, HUMAN_GLOBS), files(repo, HUMAN_GLOBS)
    touched = sorted(path for path in base_human.keys() | run_human.keys() if base_human.get(path) != run_human.get(path))
    added = sorted(set(actual) - set(expected))
    print("Protected checks modified or deleted: " + (", ".join(changed) if changed else "none"))
    print("New protected files (allowed): " + (", ".join(added) if added else "none"))
    if changed:
        return 1
    if touched:
        print("needs owner approval: " + ", ".join(touched))
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--paths", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    return check(args.repo.resolve(), args.baseline_root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
