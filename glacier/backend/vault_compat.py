"""Checks whether the plain-file vault follows common Markdown editor conventions."""

import os
import re

import yaml

import vault


_BAD_NAME_CHARACTERS = set(':*?"<>|\\')
_OBSIDIAN_LINK_CHARACTERS = set('#^[]')
_RESERVED_WINDOWS_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}
_WIKILINK = re.compile(r"(!?)\[\[([^\]]+)\]\]")
_FENCE = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?^ {0,3}\1[^\n]*(?:\n|$)", re.S)


def _without_code(text: str) -> str:
    """Mask fenced and inline code while preserving offsets and line endings."""
    text = _FENCE.sub(lambda match: re.sub(r"[^\n]", " ", match.group(0)), text)
    return re.sub(r"(`+)(.+?)\1", lambda match: re.sub(r"[^\n]", " ", match.group(0)), text, flags=re.S)


def _front_matter(text: str):
    """Return the front matter block, or its parse problem, if one is present."""
    if not text.startswith("---"):
        return None, None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, None
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            return "\n".join(lines[1:end]), None
    return None, "The opening front matter marker has no closing --- line."


def _valid_name(name: str) -> bool:
    if any(char in _BAD_NAME_CHARACTERS or ord(char) < 32 for char in name) or name.endswith((".", " ")):
        return False
    stem = name.split(".", 1)[0].upper()
    return stem not in _RESERVED_WINDOWS_NAMES


def _files():
    found = []
    for root, dirs, names in os.walk(vault.VAULT):
        dirs[:] = [name for name in dirs if name != ".git"]
        for name in names:
            relative = os.path.relpath(os.path.join(root, name), vault.VAULT).replace(os.sep, "/")
            if relative.startswith(".index.sqlite"):
                continue
            found.append(relative)
    return sorted(found)


def _resolve(target: str, files: list[str]) -> tuple[str, list[str]]:
    """Resolve a vault link by exact path, extensionless path, then unique basename."""
    target = target.strip().replace("\\", "/").lstrip("/")
    target = target.split("|", 1)[0].split("#", 1)[0].strip()
    if not target:
        return "missing", []
    exact = [path for path in files if path == target]
    if exact:
        return "found", exact
    candidates = {target.lower()}
    if not target.lower().endswith(".md"):
        candidates.add((target + ".md").lower())
    path_matches = [path for path in files if path.lower() in candidates or
                    any(path.lower().endswith("/" + candidate) for candidate in candidates)]
    if len(path_matches) == 1:
        return "found", path_matches
    if len(path_matches) > 1:
        return "ambiguous", path_matches
    # A path-like target must identify its trailing path; basename fallback applies
    # only when the link itself is a short name.
    if "/" in target:
        return "missing", []
    basename = os.path.basename(target)
    short_matches = [path for path in files if os.path.basename(path).lower() == basename.lower() or
                     (path.lower().endswith(".md") and os.path.splitext(os.path.basename(path))[0].lower() == basename.lower())]
    if len(short_matches) == 1:
        return "found", short_matches
    if len(short_matches) > 1:
        return "ambiguous", short_matches
    return "missing", []


def check_vault() -> dict:
    """Return note count and plain-language compatibility problems."""
    files = _files()
    notes = [path for path in files if path.lower().endswith(".md")]
    problems = []
    reported = set()

    def report(path: str, kind: str, detail: str, fix_hint: str):
        key = (path, kind, detail)
        if key not in reported:
            reported.add(key)
            problems.append({"path": path, "kind": kind, "detail": detail, "fix_hint": fix_hint})

    for path in files:
        parts = path.split("/")
        if any(not _valid_name(part) for part in parts):
            report(path, "invalid_filename",
                   "This file or folder name contains characters that Obsidian or Windows cannot use.",
                   "Rename it using letters, numbers, spaces, hyphens, or underscores, and avoid a dot or space at the end.")
        elif any(any(char in _OBSIDIAN_LINK_CHARACTERS for char in part) for part in parts):
            report(path, "link_unsafe_filename",
                   "This name contains #, ^, [ or ], which can break Obsidian links.",
                   "Rename it without #, ^, [ or ] so wiki links can point to it reliably.")

    for path in notes:
        try:
            with open(os.path.join(vault.VAULT, path), encoding="utf-8") as note_file:
                text = note_file.read()
        except (OSError, UnicodeError) as exc:
            report(path, "unreadable_note", f"This note could not be read: {exc}.",
                   "Open the file in a text editor and save it as UTF-8 Markdown.")
            continue

        front, front_error = _front_matter(text)
        if front_error:
            report(path, "invalid_front_matter", front_error,
                   "Add a closing --- line after the metadata, or remove the opening front matter marker.")
        elif front is not None:
            try:
                parsed = yaml.safe_load(front)
                if parsed is not None and not isinstance(parsed, dict):
                    raise ValueError("front matter must contain key and value fields")
            except (yaml.YAMLError, ValueError) as exc:
                report(path, "invalid_front_matter", f"The front matter is not valid YAML: {exc}.",
                       "Fix the metadata as YAML key and value lines; JSON-style quoted values are also valid.")

        body = text
        if front is not None:
            # Exclude metadata so text resembling a wiki link in a value is not checked as a link.
            body = text.split("\n", 1)[1]
            closing = body.find("\n---")
            body = body[closing + 4:] if closing >= 0 else body

        for embedded, raw_target in _WIKILINK.findall(_without_code(body)):
            target = raw_target.split("|", 1)[0].split("#", 1)[0].strip()
            state, matches = _resolve(target, files)
            if embedded:
                if state == "missing":
                    report(path, "missing_attachment", f"The embedded file '{target}' was not found in the vault.",
                           "Add the file to the vault or correct the name inside ![[...]].")
                elif state == "ambiguous":
                    report(path, "ambiguous_link",
                           f"The embedded file link '{target}' matches more than one file: {', '.join(matches)}.",
                           "Change the embed to include enough folder names to identify one file.")
            elif state == "missing":
                report(path, "unresolved_link", f"The link '{target}' does not match a file in the vault.",
                       "Create the note or update the link to its exact vault path or a unique file name.")
            elif state == "ambiguous":
                report(path, "ambiguous_link",
                       f"The link '{target}' matches more than one file: {', '.join(matches)}.",
                       "Change the link to include enough folder names to identify one file.")

    return {"ok": not problems, "notes_checked": len(notes), "problems": problems}
