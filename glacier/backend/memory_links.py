"""Markdown note-link parsing and Obsidian-style resolution for memory views."""

from __future__ import annotations

import os
import posixpath
import re
from urllib.parse import unquote, urlsplit


_FENCE = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?^ {0,3}\1[^\n]*(?:\n|$)", re.S)
_WIKI = re.compile(r"!?\[\[([^\]]+)\]\]")
_MARKDOWN = re.compile(r"(?<!!)\[([^\]]*)\]\((<[^>]*>|[^\s)]+)(?:\s+[^)]*)?\)")


def _mask(match: re.Match) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def _without_code(text: str) -> str:
    """Mask fenced and inline code while preserving character positions."""
    text = _FENCE.sub(_mask, text)
    return re.sub(r"(`+)(.+?)\1", _mask, text, flags=re.S)


def _target(raw: str) -> str:
    target = raw.strip().split("|", 1)[0].split("#", 1)[0].strip()
    target = unquote(target).replace("\\", "/").lstrip("/")
    if target.lower().endswith(".md"):
        target = target[:-3]
    return target.strip("/")


def parse_links(body: str) -> list[tuple[str, bool]]:
    """Return deduplicated note targets from wiki links and local Markdown links."""
    text = _without_code(body)
    found = []
    for match in _WIKI.finditer(text):
        raw = match.group(1)
        target = _target(raw)
        if target:
            found.append((target, match.group(0).startswith("!")))
    for match in _MARKDOWN.finditer(text):
        raw = match.group(2).strip("<>")
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc or raw.startswith("//"):
            continue
        target = _target(parsed.path)
        if target:
            found.append((target, False))
    return list(dict.fromkeys(found))


def _key(path: str) -> str:
    return path.replace("\\", "/").casefold()


class LinkResolver:
    """Resolve targets against one note-path snapshot in O(1) average lookup."""

    def __init__(self, paths: list[str], attachments: list[str] | None = None):
        self.paths = sorted({path.replace("\\", "/").removesuffix(".md") for path in paths}, key=_key)
        self.by_path = {_key(path): path for path in self.paths}
        self.by_name: dict[str, list[str]] = {}
        for path in self.paths:
            name = path.rsplit("/", 1)[-1].casefold()
            self.by_name.setdefault(name, []).append(path)
        self.attachments = sorted({path.replace("\\", "/") for path in (attachments or [])}, key=_key)
        self.attachments_by_name: dict[str, list[str]] = {}
        for path in self.attachments:
            self.attachments_by_name.setdefault(path.rsplit("/", 1)[-1].casefold(), []).append(path)

    def has_attachment(self, raw: str, source: str = "") -> bool:
        target = _target(raw)
        if not target:
            return False
        if "/" in target:
            key = _key(target)
            return any(_key(path) == key or _key(path).endswith("/" + key) for path in self.attachments)
        candidates = self.attachments_by_name.get(target.casefold(), [])
        if not candidates:
            return False
        source_dir = source.replace("\\", "/").rsplit("/", 1)[0] if "/" in source else ""
        return bool(candidates and (any(path.rsplit("/", 1)[0] == source_dir for path in candidates) or candidates))

    def resolve(self, raw: str, source: str = "") -> tuple[str | None, str]:
        """Return (canonical extensionless path, status), where status is resolved/unresolved."""
        target = _target(raw)
        if not target:
            return None, "unresolved"
        if target.startswith(("./", "../")):
            # Relative Markdown link: resolve against the folder of the note that contains it.
            source_dir = source.replace("\\", "/").rsplit("/", 1)[0] if "/" in source else ""
            target = posixpath.normpath(posixpath.join(source_dir, target))
            if target.startswith("../") or target == "..":
                return target, "unresolved"
        explicit = "/" in target
        if explicit:
            canonical = self.by_path.get(_key(target))
            if canonical:
                return canonical, "resolved"
            # Folder paths remain folder paths: do not fall back to basename.
            suffix = "/" + _key(target)
            candidates = [path for path in self.paths if _key(path).endswith(suffix)]
            if candidates:
                return min(candidates, key=lambda p: (p.count("/"), len(p), _key(p))), "resolved"
            return target, "unresolved"

        candidates = self.by_name.get(target.casefold(), [])
        if not candidates:
            return target, "unresolved"
        source_dir = source.replace("\\", "/").rsplit("/", 1)[0] if "/" in source else ""
        # Obsidian first prefers a matching note alongside the source, then the
        # shortest path; lexical ordering makes equal-length ties stable.
        return min(candidates, key=lambda p: (
            0 if p.rsplit("/", 1)[0] == source_dir else 1,
            p.count("/"), len(p), _key(p),
        )), "resolved"


def resolve_links(body: str, source: str, resolver: LinkResolver) -> list[dict[str, str]]:
    """Return unique resolved targets with status, preserving first-occurrence order."""
    items = []
    seen = set()
    for target, embedded in parse_links(body):
        canonical, status = resolver.resolve(target, source)
        if embedded and status == "unresolved" and resolver.has_attachment(target, source):
            continue
        if canonical is None:
            continue
        key = _key(canonical)
        if key in seen:
            continue
        seen.add(key)
        items.append({"target": canonical, "status": status})
    return items
