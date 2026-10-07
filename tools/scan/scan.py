#!/usr/bin/env python3
"""Discover maintained open-source tools as proposals; this script never installs them."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = Path(__file__).with_name("sources.yaml")
OSI_LICENSES = {
    "0bsd", "afl-3.0", "agpl-3.0", "apache-1.1", "apache-2.0", "artistic-2.0",
    "bsd-2-clause", "bsd-3-clause", "bsl-1.0", "epl-1.0", "epl-2.0",
    "eupl-1.1", "gpl-2.0", "gpl-3.0", "isc", "lgpl-2.1", "lgpl-3.0", "mit",
    "mpl-2.0", "ms-pl", "osl-3.0", "postgresql", "unlicense",
}


@dataclass(frozen=True)
class Tool:
    name: str
    license: str
    url: str
    updated: date | None
    description: str = ""
    stars: int | None = None
    source: str = ""


def _first(obj: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value: Any = obj
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if value not in (None, ""):
            return value
    return None


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _license(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("spdx_id") or value.get("name")
    return str(value or "").strip()


def _is_osi(value: str) -> bool:
    normalized = value.lower().replace(" ", "")
    return normalized in OSI_LICENSES or normalized.removesuffix("-only") in OSI_LICENSES


def _records_from_items(source: str, items: list[dict[str, Any]], today: date) -> list[Tool]:
    found = []
    for item in items:
        name = _first(item, "name", "model")
        url = _first(item, "url", "html_url", "repository.url")
        license_name = _license(_first(item, "license", "license.spdx_id"))
        updated = _date(_first(item, "pushed_at", "updated_at", "last_updated", "modified_at"))
        stars_value = _first(item, "stars", "stargazers_count")
        try:
            stars = int(stars_value) if stars_value is not None else None
        except (TypeError, ValueError):
            stars = None
        if not name or not url or not re.fullmatch(r"https?://[^\s<>()\[\]`]+", str(url)):
            continue
        if not _is_osi(license_name) or updated is None:
            continue
        if today - timedelta(days=90) > updated or updated > today:
            continue
        if source.startswith("github_") and (stars is None or stars < 50):
            continue
        found.append(Tool(str(name), license_name, str(url), updated,
                          str(_first(item, "description", "summary") or ""), stars, source))
    return found


class _OllamaHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.models: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        match = re.fullmatch(r"/library/([^/?#]+)", href)
        if match:
            self.models.add(match.group(1))


def _source_items(source: str, payload: Any) -> list[dict[str, Any]]:
    if source == "ollama":
        if isinstance(payload, dict):
            return list(payload.get("models", []))
        parser = _OllamaHTML()
        parser.feed(str(payload))
        # The model catalog does not publish OSI license/activity metadata. Keep these
        # records ineligible unless a fixture/API supplies that evidence explicitly.
        return [{"name": name, "url": f"https://ollama.com/library/{name}"} for name in parser.models]
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    if source == "mcp":
        servers = payload.get("servers", [])
        items = []
        for server in servers:
            entry = server.get("server", server) if isinstance(server, dict) else {}
            repository = entry.get("repository") or {}
            items.append({**entry, "url": entry.get("url") or repository.get("url"),
                          "updated_at": entry.get("updated_at") or entry.get("_meta", {}).get("updated_at")})
        return items
    return list(payload.get("items", []))


def _read_sources() -> dict[str, str]:
    # Sources are a deliberately tiny YAML mapping; avoid adding a runtime dependency.
    found: dict[str, str] = {}
    current = None
    for line in SOURCE_FILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^  ([a-z_]+):\s*$", line)
        if match:
            current = match.group(1)
        elif current and line.strip().startswith("url:"):
            found[current] = line.split(":", 1)[1].strip()
            current = None
    return found


def _fetch(url: str) -> Any:
    request = Request(url, headers={"User-Agent": "Glacier-tool-discovery/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type", "")
    if "json" in content_type or data.lstrip().startswith((b"{", b"[")):
        return json.loads(data.decode("utf-8"))
    return data.decode("utf-8", errors="replace")


def load_records(fixture: Path | None = None, today: date | None = None) -> list[Tool]:
    today = today or date.today()
    sources = _read_sources()
    payloads = json.loads(fixture.read_text(encoding="utf-8")) if fixture else {
        name: _fetch(url) for name, url in sources.items()
    }
    records: list[Tool] = []
    for source in sources:
        payload = payloads.get(source)
        if payload is None:
            continue
        items = _source_items(source, payload)
        records.extend(_records_from_items(source, items, today))
    # The same repository can appear in multiple GitHub topics.
    deduped: dict[str, Tool] = {}
    for record in records:
        deduped.setdefault(record.url, record)
    return list(deduped.values())


def skip_installed(records: list[Tool], setup_root: Path | None = None) -> list[Tool]:
    setup_root = setup_root or ROOT / "setup"
    paths = (setup_root / "requirements.txt", setup_root / "install_tools.sh")
    texts = [path.read_text(encoding="utf-8", errors="ignore") for path in paths if path.exists()]
    packages: set[str] = set()
    urls: set[str] = set()

    def package_key(value: str) -> str:
        return re.sub(r"[-_.]+", "-", value).lower()

    for text in texts:
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if re.search(r"(?:^|\s)(?:uv\s+)?pip\s+install\b|(?:^|\s)npm\s+install\b", line):
                tokens = line.split()
                try:
                    install_index = next(i for i, token in enumerate(tokens) if token == "install")
                except StopIteration:
                    continue
                skip_next = False
                for token in tokens[install_index + 1:]:
                    if skip_next:
                        skip_next = False
                        continue
                    if token in {"--python", "--prefix", "--target", "--registry"}:
                        skip_next = True
                        continue
                    if token.startswith("-"):
                        continue
                    if "/" in token and not token.startswith("@"):
                        continue
                    match = re.match(r"^(@[^/\s]+/[^@\s]+|[A-Za-z0-9][A-Za-z0-9._-]*)(?=$|[<>=!~\[]|@)", token)
                    if match:
                        packages.add(package_key(match.group(1)))
            else:
                match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?=$|[<>=!~\[])", line)
                if match:
                    packages.add(package_key(match.group(1)))
        for url in re.findall(r"https?://[^\s'\"<>]+", text, flags=re.IGNORECASE):
            urls.add(url.rstrip(".,;:!?)]").lower().rstrip("/"))

    return [record for record in records
            if package_key(record.name) not in packages
            and record.url.lower().rstrip("/") not in urls]


def _markdown_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"^[#>\-*`\[\]()\s]+", "", value)
    value = re.sub(r"[`\[\]()]+", "", value)
    return value[:200]


def _why(record: Tool) -> str:
    summary = record.description or "Could be useful as a locally controlled, open-source capability."
    return _markdown_text(summary)


def write_report(records: list[Tool], output_dir: Path, today: date) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"proposals-{today.isoformat()}.md"
    lines = [f"# Tool discovery proposals — {today.isoformat()}", "",
             "These are research leads for human review. This report does not install or adopt tools.", ""]
    if not records:
        lines.append("No new candidates met the license, activity, popularity, and installed-tool filters.")
    for record in records:
        lines.extend([f"## {_markdown_text(record.name)}", "", f"- License: {record.license}", f"- Link: {record.url}",
                      f"- Why it may help: {_why(record)}", "- Roadmap step: PH9.3 (tool discovery proposal; review before adoption)",
                      f"- Source: {record.source}; last active: {record.updated.isoformat() if record.updated else 'unknown'}", ""])
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def run(fixture: Path | None = None, output_dir: Path | None = None, today: date | None = None) -> Path:
    today = today or date.today()
    records = skip_installed(load_records(fixture=fixture, today=today))
    return write_report(records, output_dir or Path(__file__).parent, today)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List maintained open-source tools as proposals; never installs them.")
    parser.add_argument("--offline-fixture", type=Path, help="Read source payloads from a JSON fixture instead of the network.")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args(argv)
    try:
        report = run(fixture=args.offline_fixture, output_dir=args.output_dir)
    except Exception as exc:
        print(f"Tool scan failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote proposals to {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
