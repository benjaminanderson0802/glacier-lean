"""Shared helpers for turning exported conversations into plain notes."""

from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Iterable

from . import Note


def load_conversations(conversations_json_text: str) -> list[dict]:
    try:
        data = json.loads(conversations_json_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Please provide valid JSON containing a list of conversations.") from exc
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError("Please provide valid JSON containing a list of conversations.")
    return data


def slugify(title: object) -> str:
    value = str(title or "").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:60].rstrip("-") or "untitled"


def format_date(value: object) -> str:
    if value is None or value == "":
        return "1970-01-01"
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).date().isoformat()
        text = str(value)
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return date.fromisoformat(text[:10]).isoformat()
    except (OverflowError, OSError, ValueError, TypeError):
        return "1970-01-01"


def clean_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(part.strip() for part in value if isinstance(part, str) and part.strip())
    return ""


def note_body(source: str, source_id: str, title: str, created: str, messages: Iterable[tuple[str, str]], assistant_name: str) -> tuple[str, str]:
    visible = [(speaker, text.strip()) for speaker, text in messages if text and text.strip()]
    safe_title = title.replace("\n", " ").replace("\r", " ").replace('"', "'")
    front_matter = (
        "---\n"
        f"source: {source}\n"
        f"source_id: {source_id}\n"
        f'title: "{safe_title}"\n'
        f"created: {created}\n"
        f"message_count: {len(visible)}\n"
        "---"
    )
    sections = [f"## {'You' if speaker == 'user' else assistant_name}\n\n{text}" for speaker, text in visible]
    body_without_front_matter = "\n\n".join(sections)
    body = front_matter + ("\n\n" + body_without_front_matter if body_without_front_matter else "")
    content_hash = hashlib.sha256(body_without_front_matter.encode("utf-8")).hexdigest()
    return body, content_hash


def make_notes(source: str, conversations: list[dict], extract) -> list[Note]:
    notes = []
    used_paths: set[str] = set()
    for conversation in conversations:
        source_id, title, created, messages = extract(conversation)
        body, content_hash = note_body(source, source_id, title, created, messages, "ChatGPT" if source == "chatgpt" else "Claude")
        base = f"imports/{source}/{created}-{slugify(title)}"
        path = base + ".md"
        suffix = 2
        while path in used_paths:
            path = f"{base}-{suffix}.md"
            suffix += 1
        used_paths.add(path)
        notes.append(Note(path=path, body=body, source_id=source_id, content_hash=content_hash))
    return notes


def dedupe(notes: Iterable[Note], known_hashes: Iterable[str]) -> list[Note]:
    known = set(known_hashes)
    result = []
    for note in notes:
        if note.content_hash not in known:
            result.append(note)
            known.add(note.content_hash)
    return result
