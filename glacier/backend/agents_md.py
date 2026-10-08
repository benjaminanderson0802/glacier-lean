"""Small, bounded reader for the AGENTS.md file that applies to a project folder."""

from __future__ import annotations

import os
import re
from pathlib import Path


MAX_AGENTS_MD_BYTES = 64 * 1024


def _git_root(folder: Path) -> Path | None:
    # Both normal repositories (.git directory) and linked worktrees
    # (.git pointer file) mark the root this way. Avoid starting a Git child
    # process from a worker step just to find the search boundary.
    current = folder
    while True:
        marker = current / ".git"
        if marker.is_dir() or marker.is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def find_agents_md(folder: str | os.PathLike) -> dict[str, str] | None:
    """Find and read the closest AGENTS.md without following links outside its tree.

    In a git worktree, search from ``folder`` through the worktree root. Outside
    git, only the folder itself is considered. The file read is capped at 64 KB.
    """
    try:
        start = Path(folder).expanduser().resolve(strict=True)
        if not start.is_dir():
            return None
    except (OSError, RuntimeError, TypeError):
        return None

    root = _git_root(start)
    if root is not None:
        try:
            if os.path.commonpath((str(root), str(start))) != str(root):
                root = None
        except ValueError:
            root = None
    boundary = root or start
    current = start

    while True:
        candidate = current / "AGENTS.md"
        try:
            resolved = candidate.resolve(strict=True)
            if os.path.commonpath((str(boundary), str(resolved))) == str(boundary) and resolved.is_file():
                with resolved.open("rb") as source:
                    text = source.read(MAX_AGENTS_MD_BYTES).decode("utf-8", errors="ignore")
                text = text.replace("\r\n", "\n")  # same text whether the file was saved on Windows or not
                return {"path": str(candidate), "text": text}
        except (OSError, RuntimeError, ValueError):
            pass

        if current == boundary:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def first_heading(text: str) -> str:
    """Return the first Markdown heading, or an empty string."""
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1).strip()
    return ""


def project_instructions_detail(folder: str | os.PathLike) -> str:
    """A short line suitable for the step output shown in the Run view."""
    found = find_agents_md(folder)
    if not found:
        return ""
    heading = first_heading(found["text"])
    suffix = f" ({heading})" if heading else ""
    return f"Project instructions: AGENTS.md{suffix} — {found['path']}"
