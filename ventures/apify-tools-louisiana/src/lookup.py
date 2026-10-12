"""Rate-limited adapter for the Louisiana State Licensing Board for Contractors."""

from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE_ID = "la_lslbc_contractor_licenses"
SOURCE_NAME = "Louisiana State Licensing Board for Contractors public search"
SOURCE_SEARCH_URL = "https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByNumber"
SOURCE_NAME_SEARCH_URL = "https://arlspublic.lslbc.louisiana.gov/Public/DetailedSearch/ByName"
SOURCE_POST_URL = "https://arlspublic.lslbc.louisiana.gov/Public/_DetailedSearch/"
SOURCE_DETAIL_ROOT = "https://arlspublic.lslbc.louisiana.gov/Public/_DisplayOnlineDetails/"
MAX_RESULTS = 10
MAX_QUERY_LENGTH = 120
RATE_LIMIT_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 20


class SourceUnavailable(RuntimeError):
    """The public source could not be read or did not return valid data."""


class RateLimiter:
    """Serialize outbound requests and leave at least one second between them."""

    def __init__(self, interval_seconds: float = RATE_LIMIT_SECONDS) -> None:
        self.interval_seconds = interval_seconds
        self._next_request_at = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delay = max(0.0, self._next_request_at - now)
        if delay:
            time.sleep(delay)
            now += delay
        self._next_request_at = now + self.interval_seconds


_RATE_LIMITER = RateLimiter()


class _SearchParser(HTMLParser):
    """Extract public account names and detail keys from the search result table."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._row_depth = 0
        self._key = ""
        self._name = ""
        self._capture_name = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "tr":
            if self._row_depth == 0:
                self._key = ""
                self._name = ""
            self._row_depth += 1
        elif tag == "a" and self._row_depth == 1:
            onclick = attrs_map.get("onclick") or ""
            match = re.search(r"ShowAccountDetails\('([^']+)'", onclick)
            if match:
                self._key = match.group(1)
                self._capture_name = True

    def handle_data(self, data: str) -> None:
        if self._capture_name:
            self._name += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_name:
            self._capture_name = False
        elif tag == "tr" and self._row_depth:
            if self._row_depth == 1 and self._key and self._name.strip():
                self.rows.append({
                    "business_name": " ".join(html.unescape(self._name).split()),
                    "key": self._key,
                })
            self._row_depth -= 1


class _DetailParser(HTMLParser):
    """Read only displayed license fields, excluding contact and other personal data."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pairs: list[tuple[str, str]] = []
        self._capture: str | None = None
        self._label = ""
        self._value = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "div":
            return
        classes = (dict(attrs).get("class") or "").split()
        if "display-label" in classes:
            self._capture = "label"
            self._label = ""
        elif "display-field" in classes:
            self._capture = "value"
            self._value = ""

    def handle_data(self, data: str) -> None:
        if self._capture == "label":
            self._label += data
        elif self._capture == "value":
            self._value += data

    def handle_endtag(self, tag: str) -> None:
        if tag != "div" or self._capture is None:
            return
        if self._capture == "label":
            self._label = " ".join(self._label.split())
        else:
            value = " ".join(html.unescape(self._value).split())
            self.pairs.append((self._label, value))
        self._capture = None


def _read_url(url: str, *, data: bytes | None = None) -> str:
    _RATE_LIMITER.wait()
    headers = {
        "Accept": "text/html",
        "User-Agent": "glacier-apify-louisiana-contractor-check/0.1 (public-data lookup)",
        "X-Requested-With": "XMLHttpRequest",
    }
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Referer"] = SOURCE_SEARCH_URL
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            page = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError) as exc:
        raise SourceUnavailable("Louisiana contractor source could not be read") from exc
    if not page:
        raise SourceUnavailable("Louisiana contractor source returned an empty page")
    return page


def _search(query: str, *, license_number: bool) -> list[dict[str, str]]:
    fields = {"SearchType": "ByNumber" if license_number else "ByName"}
    if license_number:
        fields["AccountNumber"] = re.sub(r"\D", "", query)
    else:
        fields.update({"CompanyName": query, "FirstName": "", "LastName": ""})
    page = _read_url(SOURCE_POST_URL, data=urlencode(fields).encode("ascii"))
    if re.search(r"No results found for search criteria", page, re.IGNORECASE):
        return []
    if "Contractor Company Name entered must be 3 or more characters" in page:
        raise ValueError("Company name search must be at least 3 characters")
    parser = _SearchParser()
    parser.feed(page)
    if not parser.rows:
        if re.search(r"No results found for search criteria", page, re.IGNORECASE):
            return []
        raise SourceUnavailable("Louisiana contractor search response changed unexpectedly")
    return parser.rows


def _detail(row: dict[str, str]) -> list[dict[str, str | None]]:
    url = f"{SOURCE_DETAIL_ROOT}?key={row['key']}&Source=DetailedSearch"
    page = _read_url(url)
    parser = _DetailParser()
    parser.feed(page)
    records: list[dict[str, str | None]] = []
    current: dict[str, str | None] | None = None
    key_map = {
        "Type": "license_type",
        "Status": "status",
        "Effective Date": "effective_date",
        "Expiration Date": "expiration_date",
    }
    for label, value in parser.pairs:
        if label == "License":
            if current:
                records.append(current)
            current = {"license_number": value}
        elif current and label in key_map:
            current[key_map[label]] = value or None
    if current:
        records.append(current)
    if not records:
        raise SourceUnavailable("Louisiana contractor detail response has no license records")
    for record in records:
        record["source_url"] = url
        record["business_name"] = row["business_name"]
    return records


def _license_key(value: str) -> str:
    return re.sub(r"\D", "", value).lstrip("0") or "0"


def lookup_many(
    *, license_number: str | None = None, name: str | None = None, max_results: int = 1
) -> list[dict[str, object]]:
    """Return source-backed Louisiana contractor license records or explicit uncertainty."""
    if bool(license_number) == bool(name):
        raise ValueError("Provide exactly one of license_number or name")
    query = (license_number or name or "").strip()
    if not query or len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"Search text must be 1 to {MAX_QUERY_LENGTH} characters")
    if name and len(query) < 3:
        raise ValueError("Company name search must be at least 3 characters")
    if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= MAX_RESULTS:
        raise ValueError(f"max_results must be an integer from 1 to {MAX_RESULTS}")

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    checked_date = checked_at[:10]
    search_url = SOURCE_SEARCH_URL if license_number else SOURCE_NAME_SEARCH_URL
    try:
        rows = _search(query, license_number=bool(license_number))
        if name:
            lowered = query.casefold()
            rows = [row for row in rows if lowered in row["business_name"].casefold()]
        results: list[dict[str, object]] = []
        target = _license_key(query) if license_number else None
        for row in rows:
            records = _detail(row)
            if target is not None:
                records = [record for record in records
                           if _license_key(record.get("license_number") or "") == target]
            for record in records:
                status = record.get("status")
                expiration_text = record.get("expiration_date")
                expiration = None
                if expiration_text and re.fullmatch(r"\d{2}/\d{2}/\d{4}", expiration_text):
                    expiration = datetime.strptime(expiration_text, "%m/%d/%Y").date().isoformat()
                complete = bool(record.get("license_number") and status and expiration)
                outcome = "match" if complete else "uncertain — please check"
                results.append({
                    "outcome": outcome,
                    "verification_state": "verified" if complete else "uncertain",
                    "license_number": record.get("license_number"),
                    "business_name": record.get("business_name"),
                    "license_type": record.get("license_type"),
                    "status": status,
                    "effective_date": record.get("effective_date"),
                    "expiration_date": expiration,
                    "source_url": record.get("source_url"),
                    "checked_at": checked_at,
                })
                if len(results) >= max_results:
                    break
            if len(results) >= max_results:
                break
        if not results:
            if license_number and rows:
                # A partial number can return an account; exact license matching is required.
                pass
            return [{
                "outcome": f"no match found in {SOURCE_NAME} as of {checked_date}",
                "verification_state": "verified",
                "license_number": query if license_number else None,
                "business_name": None,
                "license_type": None,
                "status": None,
                "effective_date": None,
                "expiration_date": None,
                "source_url": search_url,
                "checked_at": checked_at,
            }]
        return results
    except (SourceUnavailable, ValueError, IndexError, KeyError):
        return [{
            "outcome": "uncertain — please check",
            "verification_state": "unverifiable",
            "license_number": query if license_number else None,
            "business_name": None,
            "license_type": None,
            "status": None,
            "effective_date": None,
            "expiration_date": None,
            "source_url": search_url,
            "checked_at": checked_at,
        }]


def actor_queries(actor_input: dict[str, object]) -> list[dict[str, object]]:
    """Normalize the single-query form or the bounded batch form from Actor input."""
    queries = actor_input.get("queries")
    if queries is None:
        return [{
            "license_number": actor_input.get("license_number"),
            "name": actor_input.get("name"),
            "max_results": actor_input.get("max_results", 1),
        }]
    if not isinstance(queries, list) or not queries or len(queries) > 100:
        raise ValueError("queries must contain between 1 and 100 search objects")
    normalized: list[dict[str, object]] = []
    for query in queries:
        if not isinstance(query, dict):
            raise ValueError("Each query must be an object")
        normalized.append({
            "license_number": query.get("license_number"),
            "name": query.get("name"),
            "max_results": query.get("max_results", 1),
        })
    return normalized
