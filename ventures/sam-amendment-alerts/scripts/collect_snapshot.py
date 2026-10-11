#!/usr/bin/env python3
"""Collect a complete, bounded SAM.gov Opportunities API v2 snapshot."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 20
DEFAULT_MAX_RECORDS = 2_000
MISSING_KEY_GUIDANCE = (
    "A SAM.gov API key is required. Save sam_api_key in Glacier Settings → Secrets, "
    "then retry this snapshot. Do not paste the key into a flow or chat."
)


def _resolve_sam_api_key() -> str:
    """Resolve the owner's SAM key through Glacier's OS-backed Secrets store."""
    backend = str(Path(__file__).resolve().parents[3] / "glacier" / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    try:
        import secrets_store  # type: ignore[import-not-found]

        key = secrets_store.resolve("{secret:sam_api_key}")
    except (ImportError, RuntimeError, ValueError):
        key = None
    if not isinstance(key, str) or not key.strip():
        raise ValueError(MISSING_KEY_GUIDANCE)
    return key.strip()


def _sam_request(params: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Make one read-only request and avoid leaking the key in errors."""
    query = urlencode({**params, "api_key": api_key}, doseq=True)
    request = Request(
        f"{SAM_SEARCH_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "Glacier SAM snapshot collector"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 429:
            raise ValueError("SAM.gov quota or rate limit reached; wait before retrying.") from None
        raise ValueError(f"SAM.gov Opportunities API returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Could not read a valid response from the SAM.gov Opportunities API.") from None
    if not isinstance(payload, dict):
        raise ValueError("SAM.gov returned a partial or malformed response envelope.")
    if "error" in payload or "errors" in payload:
        error = payload.get("error", payload.get("errors"))
        description = json.dumps(error, ensure_ascii=False).lower()
        if any(marker in description for marker in ("rate", "quota", "limit exceeded", "too many requests")):
            raise ValueError("SAM.gov quota or rate limit reached; wait before retrying.")
        raise ValueError("SAM.gov returned an API error instead of a result page.")
    return payload


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"SAM.gov returned a partial or malformed {field} value.")
    return value


def _check_page(payload: Any, *, expected_offset: int, page_size: int) -> tuple[int, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise ValueError("SAM.gov returned a partial or malformed result page.")
    rows = payload.get("opportunitiesData")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("SAM.gov returned a partial or malformed opportunitiesData page.")
    total = _integer(payload.get("totalRecords"), "totalRecords")
    limit = _integer(payload.get("limit"), "limit")
    offset = _integer(payload.get("offset"), "offset")
    if limit != page_size or offset != expected_offset or len(rows) > page_size:
        raise ValueError("SAM.gov returned a partial or malformed pagination page.")
    return total, rows


def _snapshot_time(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Snapshot retrieval time must include a timezone.")
    return value.astimezone(timezone.utc)


def _redact_source_value(value: Any, secret: str) -> Any:
    """Remove credential echoes from provider records before they are persisted."""
    if isinstance(value, dict):
        return {
            str(key): _redact_source_value(item, secret)
            for key, item in value.items()
            if str(key).casefold() not in {"api_key", "apikey", "access_token"}
        }
    if isinstance(value, list):
        return [_redact_source_value(item, secret) for item in value]
    if not isinstance(value, str):
        return value
    cleaned = value.replace(secret, "[REDACTED]")
    parts = urlsplit(cleaned)
    if parts.scheme in {"http", "https"} and parts.query:
        safe_query = [
            (name, item)
            for name, item in parse_qsl(parts.query, keep_blank_values=True)
            if name.casefold() not in {"api_key", "apikey", "access_token"}
        ]
        cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query, doseq=True), parts.fragment))
    return cleaned


def _write_complete_snapshot(output_path: Path, snapshot: dict[str, Any]) -> None:
    """Atomically replace the target only after every query page is complete."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=output_path.parent,
            prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = stream.name
            json.dump(snapshot, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def collect_snapshot(
    *,
    naics_codes: list[str] | tuple[str, ...] | set[str],
    output_path: str | Path | None = None,
    api_key: str | None = None,
    request_json: Callable[[dict[str, Any], str], Any] | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_records: int = DEFAULT_MAX_RECORDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fetch every result page for selected NAICS codes or fail without output."""
    codes = sorted({str(code).strip() for code in naics_codes if str(code).strip()})
    if not codes or any(not code.isdigit() or len(code) not in range(2, 7) for code in codes):
        raise ValueError("Select one or more valid NAICS codes (2 to 6 digits).")
    for name, value in (("page_size", page_size), ("max_pages", max_pages), ("max_records", max_records)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")
    if page_size > 1_000 or max_pages > 100 or max_records > 100_000:
        raise ValueError("The requested SAM.gov collection bound exceeds the safety limit.")

    key = api_key if api_key is not None else _resolve_sam_api_key()
    if not isinstance(key, str) or not key.strip():
        raise ValueError(MISSING_KEY_GUIDANCE)
    key = key.strip()
    transport = request_json or _sam_request
    retrieved = _snapshot_time(now)
    rows_by_id: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    page_coverage: list[dict[str, int]] = []
    pages_fetched = 0
    total_records = 0

    for code in codes:
        offset = 0
        expected_total: int | None = None
        code_records = 0
        code_notice_ids: set[str] = set()
        while True:
            if pages_fetched >= max_pages:
                raise ValueError("SAM.gov snapshot is incomplete: page bound reached before end of results.")
            params = {"ncode": code, "limit": page_size, "offset": offset}
            try:
                payload = transport(params, key)
            except HTTPError as exc:
                if exc.code == 429:
                    raise ValueError("SAM.gov quota or rate limit reached; wait before retrying.") from None
                raise ValueError(f"SAM.gov Opportunities API returned HTTP {exc.code}.") from None
            except (URLError, TimeoutError):
                raise ValueError("Could not retrieve a SAM.gov result page; no snapshot was saved.") from None
            page_total, page_rows = _check_page(payload, expected_offset=offset, page_size=page_size)
            if expected_total is None:
                expected_total = page_total
                if total_records + page_total > max_records:
                    raise ValueError("SAM.gov snapshot is incomplete: record bound is below the result count.")
            elif page_total != expected_total:
                raise ValueError("SAM.gov returned a partial result: totalRecords changed during pagination.")
            if offset + len(page_rows) > page_total:
                raise ValueError("SAM.gov returned a partial result page beyond totalRecords.")
            if not page_rows and offset < page_total:
                raise ValueError("SAM.gov returned an empty partial page before the end of results.")

            for row in page_rows:
                notice_id = str(row.get("noticeId") or "").strip()
                if not notice_id:
                    raise ValueError("SAM.gov returned a partial result with a notice missing noticeId.")
                if notice_id in code_notice_ids:
                    raise ValueError("SAM.gov returned a duplicate notice within one query; snapshot is incomplete.")
                code_notice_ids.add(notice_id)
                row_naics = str(row.get("naicsCode") or row.get("naics") or "").strip()
                if row_naics != code:
                    raise ValueError("SAM.gov returned a notice outside the requested NAICS scope.")
                clean_row = _redact_source_value(row, key)
                previous = rows_by_id.get(notice_id)
                if previous is not None and previous != clean_row:
                    raise ValueError("SAM.gov returned conflicting duplicate notice records; snapshot is incomplete.")
                rows_by_id[notice_id] = clean_row
                rows.append(clean_row)
            if page_rows:
                page_coverage.append({"offset": len(rows) - len(page_rows), "count": len(page_rows)})
            code_records += len(page_rows)
            pages_fetched += 1
            if len(rows) > max_records:
                raise ValueError("SAM.gov snapshot is incomplete: record bound reached before completion.")

            next_offset = offset + len(page_rows)
            if next_offset >= page_total:
                if code_records != page_total:
                    raise ValueError("SAM.gov returned a partial result: page coverage does not match totalRecords.")
                total_records += page_total
                if total_records > max_records:
                    raise ValueError("SAM.gov snapshot is incomplete: record bound reached before completion.")
                break
            if len(page_rows) != page_size:
                raise ValueError("SAM.gov returned a short page while reporting more results; snapshot is incomplete.")
            if pages_fetched >= max_pages:
                raise ValueError("SAM.gov snapshot is incomplete: page bound reached before end of results.")
            offset = next_offset

    snapshot = {
        "source": "SAM.gov Contract Opportunities API v2",
        "source_url": SAM_SEARCH_URL,
        "query_scope": {"naics_codes": codes},
        "naics_codes": codes,
        "retrieved_at": retrieved.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "retrieval_date": retrieved.date().isoformat(),
        "status": "complete",
        "complete": True,
        "pages_fetched": pages_fetched,
        "record_count": len(rows),
        "total_records": total_records,
        "totalRecords": total_records,
        "limit": page_size,
        "offset": 0,
        "page_coverage": page_coverage,
        "opportunitiesData": rows,
    }
    if output_path is not None:
        _write_complete_snapshot(Path(output_path), snapshot)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--naics", action="append", required=True, help="NAICS code to include; repeat as needed")
    parser.add_argument("--output", required=True, type=Path, help="save the complete snapshot JSON here")
    args = parser.parse_args()
    try:
        snapshot = collect_snapshot(naics_codes=args.naics, output_path=args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Saved {snapshot['record_count']} notices from {snapshot['pages_fetched']} pages to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
