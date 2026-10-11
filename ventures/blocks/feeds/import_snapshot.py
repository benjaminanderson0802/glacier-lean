"""Bounded, local-only import of owner-downloaded public feed snapshots."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import core

MAX_IMPORT_BYTES = 150_000_000
MAX_EXPANDED_ARCHIVE_BYTES = 300_000_000
MAX_ARCHIVE_MEMBERS = 5_000
MAX_IMPORT_ROWS = 1_000_000
DEFAULT_MAX_AGE_DAYS = 365


def _format_for(path: Path, declared: str | None) -> str:
    if declared:
        normalized = declared.strip().lower().lstrip(".")
        aliases = {"htm": "html", "xls": "xlsx", "tsv-zip": "zip", "jsonl": "json"}
        normalized = aliases.get(normalized, normalized)
    else:
        suffix = path.suffix.lower().lstrip(".")
        normalized = {"htm": "html", "txt": "tsv"}.get(suffix, suffix)
    if normalized not in {"json", "csv", "tsv", "zip", "xlsx", "html"}:
        raise ValueError("unsupported saved-file format; use JSON, CSV, TSV, ZIP, XLSX, or HTML")
    return normalized


def _validate_format_for_source(kind: str, format_name: str) -> None:
    supported = {
        "json": {"json_records", "cpsc_recalls_api"},
        "csv": {"osha_csv"},
        "html": {"dibbs_html"},
        "xlsx": {"cpsc_document"},
        "zip": {"nhtsa_tsv_zip", "openfda"},
        "tsv": {"nhtsa_tsv_zip"},
    }
    if kind not in supported.get(format_name, set()):
        raise ValueError(f"{format_name} is not a supported saved format for source kind {kind}")


def _reject_error_html(raw: bytes) -> None:
    prefix = raw[:8192].decode("utf-8", "replace").lstrip().casefold()
    if re.search(r"<!doctype\s+html|<html\b|<title\b", prefix):
        raise ValueError("saved source is an HTML page or error response, not the requested data file")


def _records_from_json(raw: bytes) -> tuple[list[dict[str, Any]], int | None]:
    payload = json.loads(raw.decode("utf-8-sig"))
    if isinstance(payload, list):
        source_records = payload
    elif isinstance(payload, dict):
        source_records = next((payload[key] for key in ("results", "data", "items", "records", "recalls", "result")
                               if isinstance(payload.get(key), list)), [payload])
    else:
        raise ValueError("JSON root must be a record list or object")
    if any(not isinstance(record, dict) for record in source_records):
        raise ValueError("JSON record collection contains a non-object row")
    records, total = core._records_and_total(payload)
    if not records:
        raise ValueError("JSON file contains no record collection")
    return records, total


def _records_from_csv(raw: bytes) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if not reader.fieldnames or not any(field and field.strip() for field in reader.fieldnames):
        raise ValueError("CSV file has no header row")
    if any(field is None or not field.strip() for field in reader.fieldnames):
        raise ValueError("CSV file has a blank column name")
    rows = []
    for line_number, row in enumerate(reader, 2):
        if None in row:
            raise ValueError(f"CSV row {line_number} has more values than the header")
        if any(value is None for value in row.values()):
            raise ValueError(f"CSV row {line_number} has fewer values than the header")
        if any(str(value).strip() for value in row.values()):
            rows.append(dict(row))
    if not rows:
        raise ValueError("CSV file contains no data rows")
    return rows


def _records_from_html(raw: bytes, source_url: str) -> list[dict[str, Any]]:
    text = raw.decode("utf-8-sig", "replace")
    folded = re.sub(r"\s+", " ", text).casefold()
    if "warning" in folded and ("consent" in folded or "dod" in folded):
        raise ValueError("saved DIBBS file is a warning/consent page; no acknowledgement or bypass was attempted")
    parser = core._Links()
    parser.feed(text)
    records = []
    for label, href in parser.links:
        match = re.search(r"(?:sn=|/)([A-Z0-9]{5,}-?\d{2}[A-Z0-9]+)", href, re.I)
        if match:
            records.append({"solicitation_number": match.group(1), "description": label,
                            "source_url": core.urllib.parse.urljoin(source_url, href)})
    if not records:
        raise ValueError("saved DIBBS HTML has no supported solicitation links")
    return records


def _records_from_xlsx(raw: bytes, config: dict[str, Any]) -> list[dict[str, Any]]:
    document_type = config.get("document_type")
    if document_type == "xlsx_hts":
        records = core._xlsx_hts_rows(raw)
    elif document_type == "xlsx_template":
        headers = core._xlsx_headers(raw)
        records = [{"columns": headers, "field_map": config.get("field_map", {})}] if headers else []
    else:
        records = core._xlsx_rows(raw, list(config.get("id_fields", [])) + list(config.get("expected_fields", [])))
    if not records:
        raise ValueError("XLSX file contains no supported records")
    return records


def _records_from_zip(raw: bytes, config: dict[str, Any], dictionary_path: str | Path | None) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        _check_archive_limits(archive)
        if config["kind"] == "nhtsa_tsv_zip":
            data_name = next((name for name in names if name.lower().endswith(".txt")), None)
            if not data_name:
                raise ValueError("NHTSA ZIP has no tab-delimited TXT data file")
            if dictionary_path is None:
                raise ValueError("NHTSA offline import requires the separately downloaded official RCL.txt field dictionary")
            dictionary = Path(dictionary_path).read_text(encoding="latin-1")
            columns = core._nhtsa_columns(dictionary)
            text = archive.read(data_name).decode("utf-8-sig", "replace")
            records = []
            for line_number, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                cells = line.split("\t")
                if len(cells) != len(columns):
                    raise ValueError(f"NHTSA data line {line_number} has {len(cells)} columns; expected {len(columns)}")
                records.append({columns[i]: value.strip() for i, value in enumerate(cells)})
            if not records:
                raise ValueError("NHTSA ZIP contains no data records")
            return records
        json_names = [name for name in names if name.lower().endswith(".json")]
        if not json_names:
            raise ValueError("ZIP contains no JSON partition supported by this source schema")
        records: list[dict[str, Any]] = []
        for name in json_names:
            partition, _ = _records_from_json(archive.read(name))
            records.extend(partition)
        return records


def _parse(raw: bytes, format_name: str, config: dict[str, Any], source_url: str,
           dictionary_path: str | Path | None) -> tuple[list[dict[str, Any]], int | None]:
    if format_name != "html":
        _reject_error_html(raw)
    if format_name == "json":
        return _records_from_json(raw)
    if format_name == "csv":
        return _records_from_csv(raw), None
    if format_name == "html":
        return _records_from_html(raw, source_url), None
    if format_name == "xlsx":
        return _records_from_xlsx(raw, config), None
    if format_name == "zip":
        records = _records_from_zip(raw, config, dictionary_path)
        return records, len(records)
    if format_name == "tsv":
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), delimiter="\t")
        if not reader.fieldnames or any(not field.strip() for field in reader.fieldnames):
            raise ValueError("TSV file has no valid header row")
        records = [dict(row) for row in reader]
        if not records:
            raise ValueError("TSV file contains no data rows")
        return records, len(records)
    raise ValueError(f"unsupported import format: {format_name}")


def _check_archive_limits(archive: zipfile.ZipFile) -> None:
    members = archive.infolist()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise ValueError(f"archive has more than {MAX_ARCHIVE_MEMBERS} members")
    expanded = sum(member.file_size for member in members)
    if expanded > MAX_EXPANDED_ARCHIVE_BYTES:
        raise ValueError(f"archive expands beyond the {MAX_EXPANDED_ARCHIVE_BYTES}-byte safety limit")
    if any(member.file_size > MAX_IMPORT_BYTES for member in members):
        raise ValueError(f"archive member exceeds the {MAX_IMPORT_BYTES}-byte safety limit")


def import_snapshot(source_id: str, file_path: str | Path, *, source_url: str, acquired_at: str,
                    complete: bool, format: str | None = None, max_age_days: int = DEFAULT_MAX_AGE_DAYS,
                    expected_row_count: int | None = None,
                    dictionary_path: str | Path | None = None) -> dict[str, Any]:
    """Import a complete, recent, owner-saved official file without making network requests.

    The complete flag is the owner's assertion that the saved file is a complete source snapshot.
    max_age_days bounds how long ago the file was acquired, independently of record dates.
    """
    configs = core.registry()
    if source_id not in configs:
        raise KeyError(f"Unknown feed source: {source_id}")
    if not isinstance(complete, bool) or not complete:
        return _failure(source_id, "Completeness check failed: owner must confirm the saved file is complete")
    if not isinstance(max_age_days, int) or max_age_days < 0 or max_age_days > 3650:
        raise ValueError("max_age_days must be an integer from 0 through 3650")
    try:
        acquired = date.fromisoformat(acquired_at)
    except (TypeError, ValueError) as exc:
        raise ValueError("acquired_at must be an ISO date (YYYY-MM-DD)") from exc
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", acquired_at):
        raise ValueError("acquired_at must use the YYYY-MM-DD form")
    today = datetime.now(timezone.utc).date()
    if acquired > today:
        return _failure(source_id, "Acquisition date is in the future; candidate rejected")
    if acquired < today - timedelta(days=max_age_days):
        return _failure(source_id, f"Stale input rejected: acquisition is older than {max_age_days} days")
    parsed_url = core.urllib.parse.urlparse(source_url)
    configured_url = core.urllib.parse.urlparse(configs[source_id]["url"])
    source_host = (parsed_url.hostname or "").lower().removeprefix("www.")
    configured_host = (configured_url.hostname or "").lower().removeprefix("www.")
    allowed_hosts = {configured_host}
    if source_id == "fda_enforcement":
        allowed_hosts.add("download.open.fda.gov")
    if (parsed_url.scheme != "https" or not source_host or parsed_url.username or parsed_url.password
            or source_host not in allowed_hosts):
        raise ValueError("source_url must be HTTPS and use the registered official source host")
    path = Path(file_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return _failure(source_id, f"Could not read saved source file: {exc}")
    if not raw:
        return _failure(source_id, "saved source file is empty")
    if len(raw) > MAX_IMPORT_BYTES:
        return _failure(source_id, f"saved source exceeds the {MAX_IMPORT_BYTES}-byte import limit")
    try:
        format_name = _format_for(path, format)
        _validate_format_for_source(configs[source_id]["kind"], format_name)
        if format_name == "xlsx":
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                _check_archive_limits(archive)
        records, embedded_total = _parse(raw, format_name, configs[source_id], source_url, dictionary_path)
    except (ValueError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, KeyError, OSError) as exc:
        return _failure(source_id, f"Saved source rejected: {type(exc).__name__}: {exc}")
    if len(records) > MAX_IMPORT_ROWS:
        return _failure(source_id, f"Saved source exceeds the {MAX_IMPORT_ROWS}-row import limit")
    if expected_row_count is not None and (not isinstance(expected_row_count, int) or expected_row_count < 0):
        raise ValueError("expected_row_count must be a non-negative integer")
    source_total = expected_row_count if expected_row_count is not None else embedded_total
    provenance = {"source_url": source_url, "acquired_at": acquired.isoformat(),
                  "sha256": hashlib.sha256(raw).hexdigest(), "format": format_name,
                  "complete": True, "imported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    result = core.import_snapshot_candidate(source_id, records, source_url=source_url,
                                            acquired_at=acquired.isoformat(), source_total=source_total,
                                            alerts=[], provenance=provenance)
    result.update({"format": format_name, "sha256": provenance["sha256"]})
    return result


def _has_snapshot(source_id: str) -> bool:
    with core._connect() as con:
        return bool(con.execute("SELECT 1 FROM feed_rows WHERE source_id=? LIMIT 1", (source_id,)).fetchone())


def _failure(source_id: str, alert: str) -> dict[str, Any]:
    available = _has_snapshot(source_id)
    return {"rows": len(core.query(source_id)), "changed": False,
            "status": "failed" if available else "failed_initial", "snapshot_available": available,
            "complete": False, "live_fetch": False, "idempotent": False, "alerts": [alert]}
