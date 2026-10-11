"""Recall-checker handling for the official FSIS Recall API snapshot."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

from ventures.blocks.feeds import core


def _is_fsis_url(value: str) -> bool:
    hostname = (urlparse(value).hostname or "").lower()
    return hostname == "fsis.usda.gov" or hostname.endswith(".fsis.usda.gov")


def canonical_fsis_records(records: list[dict]) -> list[dict]:
    """Collapse translated API rows to one English record per FSIS recall number."""
    grouped: dict[str, list[dict]] = {}
    unkeyed: list[dict] = []
    for record in records:
        identifier = str(record.get("field_recall_number") or record.get("field_recall_number_export") or "").strip()
        (grouped.setdefault(identifier, []) if identifier else unkeyed).append(record)

    def order(record: dict) -> tuple:
        language = str(record.get("langcode", "")).casefold()
        modified = str(record.get("field_last_modified_date", ""))
        # Prefer English; for same-language revisions prefer the newest
        # published modification value, then break ties deterministically.
        return (language != "english", tuple(-ord(char) for char in modified), json.dumps(record, sort_keys=True, ensure_ascii=False))

    canonical = [min(group, key=order).copy() for _, group in sorted(grouped.items())]
    canonical.extend(record.copy() for record in unkeyed)
    for record in canonical:
        notice_url = str(record.get("field_recall_url", ""))
        parsed = urlparse(notice_url)
        if parsed.scheme == "http" and _is_fsis_url(notice_url):
            record["field_recall_url"] = urlunparse(("https", parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return canonical


def sync_fsis_feed() -> dict:
    """Fetch and validate FSIS data, deduplicating translations before promotion."""
    source_id = "fsis_recalls"
    config = core.registry()[source_id]
    try:
        records, _source_total, alerts = core.fetch_source(source_id, config)
        canonical = canonical_fsis_records(records)
        fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        result = core._validated_snapshot_candidate(
            source_id,
            canonical,
            source_url=config["url"],
            fetched_at=fetched_at,
            # Any API total counts translated rows too, so compare only the
            # canonical recall records and let the identifier canary govern.
            source_total=None,
            alerts=list(alerts),
        )
        if result.get("status") == "ok":
            # Keep the official API endpoint in the source registry, while
            # presenting the per-record official notice as the result citation.
            with core._connect() as connection:
                for record in canonical:
                    notice_url = str(record.get("field_recall_url", ""))
                    if not notice_url.startswith("https://www.fsis.usda.gov/"):
                        continue
                    record_id = core._first(record, config.get("id_fields", []))
                    if record_id:
                        connection.execute(
                            "UPDATE feed_rows SET source_url=? WHERE source_id=? AND record_id=?",
                            (notice_url, source_id, str(record_id)),
                        )
        result["source_records"] = len(records)
        result["translation_or_duplicate_rows_removed"] = len(records) - len(canonical)
        return result
    except Exception as error:
        return core._failed_refresh(source_id, [f"Feed sync alert ({source_id}): {type(error).__name__}: {error}"])
