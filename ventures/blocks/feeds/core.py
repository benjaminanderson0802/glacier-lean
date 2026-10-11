"""Small standard-library adapters; the feed database is a rebuildable cache."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

PACKAGE = Path(__file__).parent
REGISTRY_PATH = PACKAGE / "sources.json"
USER_AGENT = "Glacier public-data client/1.0 (+https://github.com/benjaminanderson0802/glacier-lean)"
HTTP_CACHE_MAX_AGE = 300
HTTP_CACHE_MAX_BYTES = 20_000_000
_LAST_REQUEST_AT: dict[str, float] = {}


def registry() -> dict[str, dict[str, Any]]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def database_path() -> Path:
    return Path(os.environ.get("GLACIER_HOME", str(Path.home() / ".glacier"))) / "ventures" / "feeds.db"


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(target)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
      CREATE TABLE IF NOT EXISTS feed_rows (
        source_id TEXT NOT NULL, record_id TEXT NOT NULL, record_date TEXT,
        fetched_at TEXT NOT NULL, source_url TEXT NOT NULL, payload TEXT NOT NULL,
        digest TEXT NOT NULL, PRIMARY KEY(source_id, record_id));
      CREATE INDEX IF NOT EXISTS feed_rows_date ON feed_rows(source_id, record_date);
      CREATE TABLE IF NOT EXISTS feed_syncs (
        source_id TEXT PRIMARY KEY, fetched_at TEXT NOT NULL, source_total INTEGER,
        row_count INTEGER NOT NULL, digest TEXT NOT NULL, status TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS feed_schemas (
        source_id TEXT PRIMARY KEY, fields TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS feed_progress (
        source_id TEXT PRIMARY KEY, tax_year TEXT NOT NULL, source_total INTEGER NOT NULL,
        next_offset INTEGER NOT NULL, row_count INTEGER NOT NULL, fetched_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS feed_watermarks (
        source_id TEXT PRIMARY KEY, watermark TEXT NOT NULL);
    """)
    return con


def _parse_date(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    match = re.search(r"\d{4}[-/]?\d{2}[-/]?\d{2}", s)
    if not match:
        return None
    raw = match.group(0).replace("-", "").replace("/", "")
    if len(raw) != 8:
        return None
    try:
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8])).isoformat()
    except ValueError:
        return None


def _first(record: dict[str, Any], names: list[str]) -> Any:
    lower = {str(key).lower(): value for key, value in record.items()}
    for name in names:
        value = record.get(name, lower.get(name.lower()))
        if value not in (None, ""):
            return value
    return None


def _records_and_total(value: Any) -> tuple[list[dict[str, Any]], int | None]:
    if isinstance(value, list):
        return [r for r in value if isinstance(r, dict)], None
    if not isinstance(value, dict):
        return [], None
    total = value.get("total")
    if total is None and isinstance(value.get("meta"), dict):
        total = (value["meta"].get("results") or {}).get("total")
    if total is None:
        total = value.get("Count")
    try:
        total = int(total) if total is not None else None
    except (TypeError, ValueError):
        total = None
    for key in ("results", "data", "items", "records", "recalls", "result"):
        if isinstance(value.get(key), list):
            return [r for r in value[key] if isinstance(r, dict)], total
    # Some APIs return a single record object rather than a collection wrapper.
    return ([value] if value else []), total


def _request(url: str, *, timeout: int = 30, max_bytes: int | None = None) -> bytes:
    """Fetch a public GET with a descriptive client ID, bounded retries, and a small disk cache."""
    host = urllib.parse.urlparse(url).netloc
    accept = "application/json, application/rss+xml, text/csv, text/html;q=0.9, */*;q=0.8"
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    cache_path: Path | None = None
    cache_meta: dict[str, Any] = {}
    if len(url) < 4000:
        cache_root = Path(os.environ.get("GLACIER_HOME", str(Path.home() / ".glacier"))) / "ventures" / "feed-http-cache"
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        cache_path = cache_root / f"{cache_key}.body"
        meta_path = cache_root / f"{cache_key}.json"
        try:
            cache_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            cached_at = float(cache_meta.get("cached_at", 0))
            if cache_path.is_file() and time.time() - cached_at <= HTTP_CACHE_MAX_AGE:
                raw = cache_path.read_bytes()
                if max_bytes is not None and len(raw) > max_bytes:
                    raise ValueError(f"cached response exceeded the {max_bytes}-byte safety limit")
                return raw
            if cache_path.is_file() and cache_meta.get("etag"):
                headers["If-None-Match"] = cache_meta["etag"]
            if cache_path.is_file() and cache_meta.get("last_modified"):
                headers["If-Modified-Since"] = cache_meta["last_modified"]
        except (OSError, ValueError, TypeError):
            cache_meta = {}
    last_error: Exception | None = None
    for attempt in range(3):
        if host == "datacatalog.cookcountyil.gov":
            wait = 1.0 - (time.monotonic() - _LAST_REQUEST_AT.get(host, 0.0))
            if wait > 0:
                time.sleep(wait)
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if host == "datacatalog.cookcountyil.gov":
                    _LAST_REQUEST_AT[host] = time.monotonic()
                raw = response.read(max_bytes + 1) if max_bytes is not None else response.read()
                response_headers = getattr(response, "headers", {})
            if cache_path is not None and len(raw) <= HTTP_CACHE_MAX_BYTES:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(raw)
                cache_path.with_suffix(".json").write_text(json.dumps({
                    "cached_at": time.time(),
                    "etag": response_headers.get("ETag"),
                    "last_modified": response_headers.get("Last-Modified"),
                }), encoding="utf-8")
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and cache_path is not None and cache_path.is_file():
                raw = cache_path.read_bytes()
                cache_meta["cached_at"] = time.time()
                cache_path.with_suffix(".json").write_text(json.dumps(cache_meta), encoding="utf-8")
                break
            last_error = exc
            if exc.code not in (408, 425, 429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt == 2:
                raise
        time.sleep(0.5 * (2 ** attempt))
    else:
        assert last_error is not None
        raise last_error
    if max_bytes is not None and len(raw) > max_bytes:
        raise ValueError(f"download exceeded the {max_bytes}-byte safety limit")
    return raw


def _json_rows(url: str, *, timeout: int = 30) -> tuple[list[dict[str, Any]], int | None]:
    raw = _request(url, timeout=timeout)
    return _records_and_total(json.loads(raw.decode("utf-8-sig")))


def _openfda(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    # Official download index publishes each endpoint's partitions and exact totals.
    catalog = json.loads(_request("https://api.fda.gov/download.json").decode("utf-8"))
    records: list[dict[str, Any]] = []
    total = 0
    for area, label in (("food", "Food"), ("drug", "Drug"), ("device", "Device")):
        endpoint = (catalog.get("results", {}).get(area, {}) or {}).get("enforcement")
        if not endpoint:
            continue
        total += int(endpoint.get("total_records", 0))
        for partition in endpoint.get("partitions", []):
            raw = _request(partition["file"], timeout=120)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                member = next(name for name in archive.namelist() if name.endswith(".json"))
                payload = json.loads(archive.read(member).decode("utf-8"))
            chunk, _ = _records_and_total(payload)
            for record in chunk:
                record.setdefault("_openfda_dataset", label)
            records.extend(chunk)
    return records, total


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((" ".join("".join(self._text).split()), self._href))
            self._href = None


def _osha(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None, str]:
    page = _request(config["url"], timeout=30, max_bytes=5_000_000).decode("utf-8", "replace")
    parser = _Links()
    parser.feed(page)
    found = [(label, urllib.parse.urljoin(config["url"], href)) for label, href in parser.links if "Summary Data" in label and re.search(r"\d{4}", label)]
    if not found:
        raise ValueError("OSHA current Summary Data download link was not found; page format may have changed")
    # Current summary link is first in the Current ITA Data section on the official page.
    label, url = found[0]
    # OSHA publishes hundreds of thousands of establishments. Bound both the
    # transfer and the row loop so a page/schema change cannot run indefinitely.
    raw = _request(url, timeout=120, max_bytes=150_000_000)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", "replace")))
    rows: list[dict[str, Any]] = []
    for row in reader:
        if len(rows) >= 1_000_000:
            raise ValueError("OSHA summary exceeded the 1,000,000-row safety limit")
        rows.append(row)
    if not reader.fieldnames:
        raise ValueError("OSHA summary CSV has no header row")
    return rows, len(rows), url


def _socrata(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    # Called only for small, fixture-sized data. Production uses the streaming path below.
    max_rows, _ = _json_rows(config["url"] + "?$select=max(year)", timeout=120)
    year = str(max_rows[0].get("max_year", "")).removesuffix(".0")
    where = urllib.parse.quote(f"year='{year}'", safe="'=")
    count_rows, _ = _json_rows(config["url"] + f"?$select=count(*)&$where={where}", timeout=120)
    total = int(next(iter(count_rows[0].values()))) if count_rows else None
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        selected = ",".join(config.get("selected_fields", []))
        url = config["url"] + f"?$select={selected}&$where={where}&$order=pin&$limit=50000&$offset=" + str(offset)
        chunk, _ = _json_rows(url, timeout=120)
        rows.extend(chunk)
        offset += len(chunk)
        if not chunk or (total is not None and offset >= total):
            break
    return rows, total


def _sync_socrata_stream(source_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Resume the latest-year roll in bounded pages; publish only a complete snapshot."""
    max_rows, _ = _json_rows(config["url"] + "?$select=max(year)", timeout=120)
    year = str(max_rows[0].get("max_year", "")).removesuffix(".0")
    if not year:
        raise ValueError("Cook County Assessor dataset did not publish its latest tax year")
    clauses = [f"year='{year}'"]
    township_codes = config.get("target_township_codes", [])
    property_classes = config.get("target_classes", [])
    if township_codes:
        clauses.append("township_code in (" + ",".join("'" + str(code).replace("'", "") + "'" for code in township_codes) + ")")
    if property_classes:
        clauses.append("class in (" + ",".join("'" + str(code).replace("'", "") + "'" for code in property_classes) + ")")
    where = urllib.parse.quote(" AND ".join(clauses), safe="'(),=:")
    count_rows, _ = _json_rows(config["url"] + f"?$select=count(*)&$where={where}", timeout=45)
    total = int(next(iter(count_rows[0].values()))) if count_rows else None
    if total is None or total <= 0:
        raise ValueError("Cook County Assessor did not publish a positive current-year row total")
    selected = ",".join(config["selected_fields"])
    source_url = config["url"] + f"?$select={selected}&$where={where}"
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    target = database_path()
    with _connect(target) as con:
        con.execute("CREATE TABLE IF NOT EXISTS feed_stage (source_id TEXT NOT NULL, record_id TEXT NOT NULL, record_date TEXT, fetched_at TEXT NOT NULL, source_url TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(source_id, record_id))")
        progress = con.execute("SELECT tax_year,source_total,next_offset,row_count,fetched_at FROM feed_progress WHERE source_id=?", (source_id,)).fetchone()
        watermark_row = con.execute("SELECT watermark FROM feed_watermarks WHERE source_id=?", (source_id,)).fetchone()
        if progress is None or progress[0] != year or progress[1] != total:
            if progress is None and watermark_row is not None:
                offset, staged_count = 0, 0
            else:
                con.execute("DELETE FROM feed_stage WHERE source_id=?", (source_id,))
                con.execute("DELETE FROM feed_progress WHERE source_id=?", (source_id,))
                offset, staged_count, fetched_at = 0, 0, fetched_at
        else:
            offset, staged_count, fetched_at = progress[2], progress[3], progress[4]
    if progress is None and watermark_row is not None:
        return _sync_socrata_incremental(source_id, config, where, total, watermark_row[0], fetched_at)
    alerts: list[str] = []
    page_size = max(1, min(int(config.get("page_size", 10000)), 50000))
    max_pages = max(1, int(config.get("max_pages_per_sync", 5)))
    pages = 0
    while offset < total and pages < max_pages:
        url = source_url + "&$order=pin&$limit=" + str(page_size) + "&$offset=" + str(offset)
        chunk, _ = _json_rows(url, timeout=45)
        if not chunk:
            break
        rows, page_alerts = normalize_rows(source_id, chunk, source_url=source_url, fetched_at=fetched_at)
        alerts.extend(page_alerts)
        inserts = []
        for row in rows:
            digest = hashlib.sha256(json.dumps(row["data"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            inserts.append((row["source_id"], row["record_id"], row["record_date"], row["fetched_at"], row["source_url"], json.dumps(row["data"], ensure_ascii=False), digest))
        with _connect(target) as con:
            con.executemany("INSERT OR REPLACE INTO feed_stage(source_id,record_id,record_date,fetched_at,source_url,payload,digest) VALUES(?,?,?,?,?,?,?)", inserts)
            offset += len(chunk)
            staged_count += len(rows)
            con.execute("INSERT INTO feed_progress(source_id,tax_year,source_total,next_offset,row_count,fetched_at) VALUES(?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET tax_year=excluded.tax_year,source_total=excluded.source_total,next_offset=excluded.next_offset,row_count=excluded.row_count,fetched_at=excluded.fetched_at", (source_id, year, total, offset, staged_count, fetched_at))
            con.execute("INSERT INTO feed_syncs(source_id,fetched_at,source_total,row_count,digest,status) VALUES(?,?,?,?,?,'in_progress') ON CONFLICT(source_id) DO UPDATE SET fetched_at=excluded.fetched_at,source_total=excluded.source_total,row_count=excluded.row_count,status='in_progress'", (source_id, fetched_at, total, offset, ""))
        pages += 1
    if staged_count == 0:
        raise ValueError("Cook County Assessor download returned no rows; existing snapshot retained")
    complete = offset >= total
    if not complete:
        alerts.append(f"Sync progress: staged {offset} of {total} Cook County rows for tax year {year}; the next run will continue from row {offset}. The previous complete snapshot remains active.")
        return {"rows": staged_count, "changed": False, "complete": False,
                "progress": {"downloaded": offset, "total": total, "tax_year": year}, "alerts": alerts}
    if abs(staged_count - total) / total > 0.01:
        alerts.append(f"Row-count alert: normalized {staged_count} of {total} Cook County rows for tax year {year}")
    with _connect(target) as con:
        staged = con.execute("SELECT record_id,digest FROM feed_stage WHERE source_id=? ORDER BY record_id", (source_id,)).fetchall()
    if not any(row[0] for row in staged):
        alerts.append("Canary alert: Cook County parcel identifiers did not parse")
    digest = hashlib.sha256("\n".join(sorted(row[1] for row in staged)).encode()).hexdigest()
    watermark_rows, _ = _json_rows(config["url"] + f"?$select=max(:updated_at)&$where={where}", timeout=45)
    watermark = next(iter(watermark_rows[0].values()), None) if watermark_rows else None
    if not watermark:
        raise ValueError("Cook County Socrata :updated_at watermark is unavailable; complete snapshot retained")
    with _connect(target) as con:
        previous = con.execute("SELECT digest FROM feed_syncs WHERE source_id=?", (source_id,)).fetchone()
        changed = previous is None or previous[0] != digest
        con.execute("DELETE FROM feed_rows WHERE source_id=?", (source_id,))
        con.execute("INSERT INTO feed_rows SELECT source_id,record_id,record_date,fetched_at,source_url,payload,digest FROM feed_stage WHERE source_id=?", (source_id,))
        con.execute("DELETE FROM feed_stage WHERE source_id=?", (source_id,))
        con.execute("DELETE FROM feed_progress WHERE source_id=?", (source_id,))
        con.execute("INSERT INTO feed_watermarks(source_id,watermark) VALUES(?,?) ON CONFLICT(source_id) DO UPDATE SET watermark=excluded.watermark", (source_id, str(watermark)))
        con.execute("INSERT INTO feed_syncs(source_id,fetched_at,source_total,row_count,digest,status) VALUES(?,?,?,?,?,'ok') ON CONFLICT(source_id) DO UPDATE SET fetched_at=excluded.fetched_at,source_total=excluded.source_total,row_count=excluded.row_count,digest=excluded.digest,status='ok'", (source_id, fetched_at, total, staged_count, digest))
    return {"rows": staged_count, "changed": bool(changed), "complete": True, "alerts": alerts}


def _sync_socrata_incremental(source_id: str, config: dict[str, Any], where: str, source_total: int,
                              watermark: str, fetched_at: str) -> dict[str, Any]:
    """Upsert only rows changed since the last complete selected snapshot."""
    field = config.get("incremental_field", ":updated_at")
    incremental_where = urllib.parse.quote(
        urllib.parse.unquote(where) + f" AND {field} > '{watermark}'", safe="'(),=:"
    )
    selected = ",".join(config["selected_fields"])
    source_url = config["url"] + f"?$select={selected}&$where={incremental_where}"
    page_size = max(1, min(int(config.get("page_size", 10000)), 50000))
    max_pages = max(1, int(config.get("max_pages_per_sync", 5)))
    rows_seen = 0
    pages = 0
    latest = watermark
    alerts: list[str] = []
    exhausted = False
    while pages < max_pages:
        url = source_url + "&$order=" + urllib.parse.quote(field, safe=":") + "&$limit=" + str(page_size) + "&$offset=" + str(rows_seen)
        chunk, _ = _json_rows(url, timeout=45)
        if not chunk:
            exhausted = True
            break
        normalized, page_alerts = normalize_rows(source_id, chunk, source_url=source_url, fetched_at=fetched_at)
        alerts.extend(page_alerts)
        inserts = []
        for row, original in zip(normalized, chunk):
            value = _first(original, [field])
            if value and str(value) > latest:
                latest = str(value)
            digest = hashlib.sha256(json.dumps(row["data"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            inserts.append((row["source_id"], row["record_id"], row["record_date"], row["fetched_at"], row["source_url"], json.dumps(row["data"], ensure_ascii=False), digest))
        with _connect() as con:
            con.executemany("INSERT OR REPLACE INTO feed_rows(source_id,record_id,record_date,fetched_at,source_url,payload,digest) VALUES(?,?,?,?,?,?,?)", inserts)
        rows_seen += len(chunk)
        pages += 1
        if len(chunk) < page_size:
            exhausted = True
            break
    complete = exhausted or rows_seen == 0
    if not complete:
        alerts.append(f"Incremental sync progress: read {rows_seen} changed Cook County rows in {max_pages} pages; watermark held for next run.")
        return {"rows": rows_seen, "changed": bool(rows_seen), "complete": False, "alerts": alerts}
    with _connect() as con:
        row_count, digest = con.execute("SELECT COUNT(*),COALESCE(group_concat(digest,''),'') FROM feed_rows WHERE source_id=?", (source_id,)).fetchone()
        rows = con.execute("SELECT digest FROM feed_rows WHERE source_id=? ORDER BY record_id", (source_id,)).fetchall()
        digest = hashlib.sha256("\n".join(row[0] for row in rows).encode()).hexdigest()
        con.execute("INSERT INTO feed_watermarks(source_id,watermark) VALUES(?,?) ON CONFLICT(source_id) DO UPDATE SET watermark=excluded.watermark", (source_id, latest))
        con.execute("INSERT INTO feed_syncs(source_id,fetched_at,source_total,row_count,digest,status) VALUES(?,?,?,?,?,'ok') ON CONFLICT(source_id) DO UPDATE SET fetched_at=excluded.fetched_at,source_total=excluded.source_total,row_count=excluded.row_count,digest=excluded.digest,status='ok'", (source_id, fetched_at, source_total, row_count, digest))
    if source_total and abs(row_count - source_total) / source_total > 0.01:
        alerts.append(f"Row-count alert: normalized {row_count} of {source_total} selected Cook County rows (difference exceeds 1%).")
    return {"rows": rows_seen, "changed": bool(rows_seen), "complete": True, "alerts": alerts}


def _nhtsa(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    raw = _request(config["url"], timeout=120)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        filename = next(name for name in archive.namelist() if name.lower().endswith(".txt"))
        text = archive.read(filename).decode("utf-8-sig", "replace")
    # NHTSA's published RCL dictionary identifies column positions. Keep columns stable by name.
    dict_text = _request(config["dictionary_url"]).decode("latin-1", "replace")
    columns = _nhtsa_columns(dict_text)
    result = []
    for line in text.splitlines():
        cells = line.split("\t")
        if not line.strip():
            continue
        result.append({columns[i] if i < len(columns) else f"field_{i + 1}": val.strip() for i, val in enumerate(cells)})
    return result, len(result)


def _cpsc_recalls(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int, list[str]]:
    start_year = int(config.get("history_start_year", 1973))
    last_year = date.today().year
    rows: list[dict[str, Any]] = []
    for first_year in range(start_year, last_year + 1, 5):
        end_year = min(first_year + 4, last_year)
        query = urllib.parse.urlencode({
            "format": "json",
            "RecallDateStart": f"{first_year}-01-01",
            "RecallDateEnd": f"{end_year}-12-31",
        })
        chunk, _ = _json_rows(config["url"] + "?" + query, timeout=int(config.get("request_timeout_seconds", 30)))
        rows.extend(chunk)
    # RecallNumber is the published stable key; de-duplicate inclusive boundary cases.
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(_first(row, config.get("id_fields", ["RecallNumber"])) or json.dumps(row, sort_keys=True))
        unique[key] = row
    return list(unique.values()), None, []


def _nhtsa_columns(dictionary: str) -> list[str]:
    """Read the numbered field table in NHTSA's RCL.txt dictionary."""
    found: dict[int, str] = {}
    for line in dictionary.splitlines():
        match = re.match(r"\s*(\d+)\s+([A-Z][A-Z0-9_]*)\s+", line)
        if match:
            found[int(match.group(1))] = match.group(2)
    if not found or sorted(found) != list(range(1, max(found) + 1)):
        raise ValueError("NHTSA RCL dictionary field table is incomplete or changed format")
    return [found[index] for index in range(1, max(found) + 1)]


def _dibbs(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None, list[str]]:
    # Public browse/search endpoint; do not submit bids or access authenticated data.
    raw = _request(config["url"]).decode("utf-8", "replace")
    page_text = re.sub(r"\s+", " ", raw).casefold()
    if "warning" in page_text and ("consent" in page_text or "dod" in page_text):
        raise ValueError("DIBBS public source redirected to the DoD warning/consent page; no public solicitation feed is available without user acknowledgement. No acknowledgement or login was attempted. An owner must verify the official solicitation at https://www.dibbs.bsm.dla.mil/ and enter its exact link and details in the venture's local solicitations.json intake.")
    parser = _Links()
    parser.feed(raw)
    rows = []
    for label, href in parser.links:
        match = re.search(r"(?:sn=|/)([A-Z0-9]{5,}-?\d{2}[A-Z0-9]+)", href, re.I)
        if match:
            rows.append({"solicitation_number": match.group(1), "description": label, "source_url": urllib.parse.urljoin(config["url"], href)})
    alerts = ["DIBBS public landing-page parse is a discovery adapter; its authenticated/search listing format is not a documented bulk feed."]
    if not rows:
        alerts.append("No solicitation rows were found on the public page; DIBBS may have changed its page format or requires its public search form.")
    return rows, None, alerts


def _xlsx_rows(raw: bytes, header_hints: list[str] | None = None) -> list[dict[str, Any]]:
    """Read the first worksheet of a public .xlsx file without extra packages."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        strings: list[str] = []
        try:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(text.text or "" for text in item.iter() if text.tag.endswith("}t")) for item in root]
        except KeyError:
            pass
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    matrix: list[list[str]] = []
    for row in sheet.iter():
        if not row.tag.endswith("}row"):
            continue
        cells: dict[int, str] = {}
        for cell in row:
            if not cell.tag.endswith("}c"):
                continue
            ref = cell.attrib.get("r", "")
            letters = "".join(ch for ch in ref if ch.isalpha())
            col = 0
            for char in letters.upper():
                col = col * 26 + ord(char) - 64
            col = max(0, col - 1)
            value_node = next((item for item in cell if item.tag.endswith("}v")), None)
            value = value_node.text if value_node is not None and value_node.text else ""
            if cell.attrib.get("t") == "s" and value:
                value = strings[int(value)]
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(item.text or "" for item in cell.iter() if item.tag.endswith("}t"))
            cells[col] = value
        if cells:
            matrix.append([cells.get(index, "") for index in range(max(cells) + 1)])
    hints = {value.casefold().strip() for value in (header_hints or [])}
    header_index = next((i for i, row in enumerate(matrix)
                         if any(any(hint in str(value).casefold().strip() for hint in hints)
                                for value in row if str(value).strip())), None)
    if header_index is None:
        header_index = next((i for i, row in enumerate(matrix) if any(str(value).strip() for value in row)), None)
    if header_index is None:
        return []
    headers = [str(value).strip() for value in matrix[header_index]]
    records = []
    for values in matrix[header_index + 1:]:
        record = {header: values[i] if i < len(values) else "" for i, header in enumerate(headers) if header}
        if any(str(value).strip() for value in record.values()):
            records.append(record)
    return records


def _cpsc_document(config: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None, str]:
    library_url = config["url"]
    page = _request(library_url).decode("utf-8", "replace")
    links = _Links()
    links.feed(page)
    wanted = str(config["title_match"]).casefold()
    found = next(((label, urllib.parse.urljoin(library_url, href)) for label, href in links.links
                  if wanted in label.casefold() or wanted in href.casefold()), None)
    if found is None:
        raise ValueError(f"CPSC document library link not found: {config['title_match']}")
    _, document_url = found
    raw = _request(document_url, timeout=120)
    if config.get("document_type") == "pdf_hts":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        codes = sorted(set(re.findall(r"\b(?:\d{4}\.\d{2}\.\d{2}(?:\.\d{2})?|\d{10})\b", text)))
        return [{"tariff_code": code} for code in codes], len(codes), document_url
    if config.get("document_type") == "xlsx_hts":
        records = _xlsx_hts_rows(raw)
        return records, len(records), document_url
    if config.get("document_type") == "xlsx_template":
        headers = _xlsx_headers(raw)
        return [{"columns": headers, "field_map": config.get("field_map", {})}], 1, document_url
    rows = _xlsx_rows(raw, list(config.get("id_fields", [])) + list(config.get("expected_fields", [])))
    return rows, len(rows), document_url


def _xlsx_hts_rows(raw: bytes) -> list[dict[str, Any]]:
    """Read the CP1/CP2 tabs in CPSC's current HTS workbook."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        strings: list[str] = []
        try:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(text.text or "" for text in item.iter() if text.tag.endswith("}t")) for item in root]
        except KeyError:
            pass
        records: list[dict[str, Any]] = []
        for name in ("xl/worksheets/sheet2.xml", "xl/worksheets/sheet3.xml"):
            sheet = ET.fromstring(archive.read(name))
            matrix: list[list[str]] = []
            for row in sheet.iter():
                if not row.tag.endswith("}row"):
                    continue
                cells: dict[int, str] = {}
                for cell in row:
                    if not cell.tag.endswith("}c"):
                        continue
                    ref = cell.attrib.get("r", "")
                    letters = "".join(ch for ch in ref if ch.isalpha())
                    col = 0
                    for char in letters.upper():
                        col = col * 26 + ord(char) - 64
                    value_node = next((item for item in cell if item.tag.endswith("}v")), None)
                    value = value_node.text if value_node is not None and value_node.text else ""
                    if cell.attrib.get("t") == "s" and value:
                        value = strings[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(item.text or "" for item in cell.iter() if item.tag.endswith("}t"))
                    cells[max(col - 1, 0)] = value.strip()
                if cells:
                    matrix.append([cells.get(i, "") for i in range(max(cells) + 1)])
            header_idx = next((idx for idx, row in enumerate(matrix) if any(value.strip().casefold() == "hts code" for value in row)), None)
            if header_idx is None:
                raise ValueError(f"CPSC HTS workbook tab has no HTS Code column: {name}")
            headers = [value.strip() for value in matrix[header_idx]]
            for values in matrix[header_idx + 1:]:
                record = {header: (values[i] if i < len(values) else "") for i, header in enumerate(headers) if header}
                code = next((value.strip() for header, value in record.items() if header.strip().casefold() == "hts code"), "")
                if code:
                    records.append({"tariff_code": code, **record})
    return records


def _xlsx_headers(raw: bytes) -> list[str]:
    """Return the first non-empty row as column names for a blank upload template."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        strings: list[str] = []
        try:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(text.text or "" for text in item.iter() if text.tag.endswith("}t")) for item in root]
        except KeyError:
            pass
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    for row in sheet.iter():
        if not row.tag.endswith("}row"):
            continue
        cells: dict[int, str] = {}
        for cell in row:
            if not cell.tag.endswith("}c"):
                continue
            ref = cell.attrib.get("r", "")
            letters = "".join(ch for ch in ref if ch.isalpha())
            col = 0
            for char in letters.upper():
                col = col * 26 + ord(char) - 64
            value_node = next((item for item in cell if item.tag.endswith("}v")), None)
            value = value_node.text if value_node is not None and value_node.text else ""
            if cell.attrib.get("t") == "s" and value:
                value = strings[int(value)]
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(item.text or "" for item in cell.iter() if item.tag.endswith("}t"))
            cells[max(col - 1, 0)] = value
        if cells and any(value.strip() for value in cells.values()):
            return [cells.get(index, "").strip() for index in range(max(cells) + 1)]
    return []


def fetch_source(source_id: str, config: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None, list[str]]:
    kind = config["kind"]
    alerts: list[str] = []
    source_url = config["url"]
    if kind == "openfda":
        records, total = _openfda(config)
    elif kind == "nhtsa_tsv_zip":
        records, total = _nhtsa(config)
    elif kind == "osha_csv":
        records, total, source_url = _osha(config)
    elif kind == "socrata":
        records, total = _socrata(config)
    elif kind == "cpsc_recalls_api":
        records, total, alerts = _cpsc_recalls(config)
    elif kind == "dibbs_html":
        records, total, alerts = _dibbs(config)
    elif kind == "cpsc_document":
        records, total, source_url = _cpsc_document(config)
    else:
        records, total = _json_rows(source_url)
    return records, total, alerts


def normalize_rows(source_id: str, records: list[dict[str, Any]], *, source_url: str, fetched_at: str | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    config = registry().get(source_id, {})
    id_fields = list(config.get("id_fields", [])) + ["id", "record_id", "identifier", "recall_number"]
    date_fields = list(config.get("date_fields", [])) + ["date", "record_date", "updated_at", "created_at", "recall_date", "report_date"]
    fetched_at = fetched_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows: list[dict[str, Any]] = []
    alerts: list[str] = []
    fields: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            alerts.append(f"Format alert: row {index} is not an object")
            continue
        fields.update(map(str, record.keys()))
        composite_fields = list(config.get("composite_id_fields", []))
        composite_values = [_first(record, [name]) for name in composite_fields]
        record_id = (
            "|".join(str(value) for value in composite_values)
            if composite_fields and all(value is not None for value in composite_values)
            else _first(record, id_fields)
        )
        if record_id is None:
            # Stable content-derived id for rows without a published primary key.
            record_id = hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest()[:24]
        record_date = _parse_date(_first(record, date_fields))
        payload = json.loads(json.dumps(record, ensure_ascii=False, default=str))
        rows.append({"source_id": source_id, "record_id": str(record_id), "record_date": record_date, "fetched_at": fetched_at, "source_url": source_url, "data": payload})
    expected = set(config.get("expected_fields", []))
    if records and not config:
        alerts.append(f"Format alert: unregistered source schema observed fields: {', '.join(sorted(fields))}")
    if records and expected and not any(name.lower() in {field.lower() for field in fields} for name in expected):
        alerts.append(f"Format alert: none of the expected fields were found; observed fields: {', '.join(sorted(fields)[:20])}")
    with _connect() as con:
        prior = con.execute("SELECT fields FROM feed_schemas WHERE source_id=?", (source_id,)).fetchone()
        current = sorted(fields)
        if prior:
            previous = set(json.loads(prior[0]))
            if previous != fields:
                added, removed = sorted(fields - previous), sorted(previous - fields)
                alerts.append(f"Format alert: schema changed (added: {added}; removed: {removed})")
        con.execute("INSERT INTO feed_schemas(source_id, fields) VALUES (?, ?) ON CONFLICT(source_id) DO UPDATE SET fields=excluded.fields", (source_id, json.dumps(current)))
    return rows, alerts


def store_snapshot(source_id: str, rows: list[dict[str, Any]], *, db_path: Path | None = None, source_total: int | None = None, source_url: str = "") -> int:
    row_digests = [(r, hashlib.sha256(json.dumps(r["data"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()) for r in rows]
    digest = hashlib.sha256("\n".join(sorted(d for _, d in row_digests)).encode()).hexdigest()
    fetched_at = rows[0]["fetched_at"] if rows else datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as con:
        prior = con.execute("SELECT digest FROM feed_syncs WHERE source_id=?", (source_id,)).fetchone()
        changed = prior is None or prior[0] != digest
        # Replace only after a complete fetch so errors never erase the last good snapshot.
        con.execute("DELETE FROM feed_rows WHERE source_id=?", (source_id,))
        con.executemany("INSERT OR REPLACE INTO feed_rows(source_id, record_id, record_date, fetched_at, source_url, payload, digest) VALUES (?, ?, ?, ?, ?, ?, ?)", [(r["source_id"], r["record_id"], r["record_date"], r["fetched_at"], r["source_url"] or source_url, json.dumps(r["data"], ensure_ascii=False), d) for r, d in row_digests])
        con.execute("INSERT INTO feed_syncs(source_id, fetched_at, source_total, row_count, digest, status) VALUES (?, ?, ?, ?, ?, 'ok') ON CONFLICT(source_id) DO UPDATE SET fetched_at=excluded.fetched_at, source_total=excluded.source_total, row_count=excluded.row_count, digest=excluded.digest, status='ok'", (source_id, fetched_at, source_total, len(rows), digest))
    return int(changed)


def sync(source_id: str) -> dict[str, Any]:
    configs = registry()
    if source_id not in configs:
        raise KeyError(f"Unknown feed source: {source_id}")
    config = configs[source_id]
    try:
        if config["kind"] == "socrata":
            return _sync_socrata_stream(source_id, config)
        records, source_total, alerts = fetch_source(source_id, config)
        fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        rows, format_alerts = normalize_rows(source_id, records, source_url=config["url"], fetched_at=fetched_at)
        alerts.extend(format_alerts)
        if not records:
            raise ValueError("source returned no records; existing snapshot retained")
        canary = config.get("canary", {}).get("field")
        if canary and not any(_first(record, [canary, "id", "record_id", "identifier"]) is not None for record in records):
            alerts.append(f"Canary alert: no records included expected identifier field {canary}")
        if source_total is not None:
            if len(rows) < source_total:
                alerts.append(f"Row-count alert: downloaded {len(rows)} of {source_total} source rows")
            if source_total and abs(len(rows) - source_total) / source_total > 0.01:
                alerts.append(f"Row-count alert: normalized rows differ from source total by more than 1% ({len(rows)} vs {source_total})")
        changed = bool(store_snapshot(source_id, rows, source_total=source_total, source_url=config["url"]))
        return {"rows": len(rows), "changed": changed, "alerts": alerts}
    except Exception as exc:
        alert = f"Feed sync alert ({source_id}): {type(exc).__name__}: {exc}"
        with _connect() as con:
            con.execute("INSERT INTO feed_syncs(source_id, fetched_at, source_total, row_count, digest, status) VALUES (?, ?, NULL, 0, '', 'error') ON CONFLICT(source_id) DO UPDATE SET fetched_at=excluded.fetched_at, status='error'", (source_id, datetime.now(timezone.utc).isoformat()))
            existing = con.execute("SELECT row_count FROM feed_syncs WHERE source_id=?", (source_id,)).fetchone()
        return {"rows": existing[0] if existing else 0, "changed": False, "alerts": [alert]}


def sync_all() -> dict[str, dict[str, Any]]:
    return {source_id: sync(source_id) for source_id in registry()}


def query(source_id: str, *, db_path: Path | None = None, **filters: Any) -> list[dict[str, Any]]:
    allowed = {"record_id", "record_date", "fetched_at"}
    unknown = set(filters) - allowed
    if unknown:
        raise ValueError(f"Unsupported feed filters: {', '.join(sorted(unknown))}")
    where = ["source_id=?"]
    params: list[Any] = [source_id]
    for key, value in filters.items():
        where.append(f"{key}=?")
        params.append(value)
    with _connect(db_path) as con:
        rows = con.execute("SELECT record_id, record_date, fetched_at, source_url, payload FROM feed_rows WHERE " + " AND ".join(where) + " ORDER BY record_date DESC, record_id", params).fetchall()
    return [{"source_id": source_id, "record_id": r[0], "record_date": r[1], "fetched_at": r[2], "source_url": r[3], "data": json.loads(r[4])} for r in rows]
