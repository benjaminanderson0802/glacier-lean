"""Pure parsers for locally exported conversations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Note:
    path: str
    body: str
    source_id: str
    content_hash: str
