"""Rate-limited adapter for Mississippi's public contractor lookup."""

from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE_ID = "ms_msboc_contractor_licenses"
SOURCE_NAME = "Mississippi State Board of Contractors public contractor search"
SOURCE_SEARCH_URL = "https://search.msboc.us/ConsolidatedSearch.cfm"
SOURCE_RESULTS_URL = "https://search.msboc.us/ConsolidatedResults.cfm?ContractorType=&VarDatasource=BOC"
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


class _ResultsParser(HTMLParser):
    """Extract result rows and detail links from the board's HTML table."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._row_depth = 0
        self._cell_depth = 0
        self._cells: list[str] = []
        self._cell_parts: list[str] = []
        self._detail_url = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "tr":
            if self._row_depth == 0:
                self._cells = []
                self._detail_url = ""
            self._row_depth += 1
        elif tag == "td" and self._row_depth == 1:
            self._cell_depth += 1
            if self._cell_depth == 1:
                self._cell_parts = []
        elif tag == "a":
            href = attrs_map.get("href") or ""
            if "Detail.cfm?" in href:
                self._detail_url = href

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._row_depth == 1 and self._cell_depth:
            self._cell_depth -= 1
            if self._cell_depth == 0:
                self._cells.append(" ".join("".join(self._cell_parts).split()))
        elif tag == "tr" and self._row_depth:
            if self._row_depth == 1 and self._detail_url and len(self._cells) >= 5:
                cells = self._cells
                license_status = cells[3]
                match = re.match(r"([A-Za-z0-9-]+)\s*(.*)", license_status)
                if match:
                    self.rows.append({
                        "license_number": match.group(1),
                        "listing_status": match.group(2).strip(),
                        "business_name": cells[2].strip(),
                        "detail_url": self._detail_url,
                    })
            self._row_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._cell_depth:
            self._cell_parts.append(data)


def _read_url(url: str, *, data: bytes | None = None) -> str:
    _RATE_LIMITER.wait()
    headers = {
        "Accept": "text/html",
        "User-Agent": "glacier-apify-ms-contractor-check/0.1 (public-data lookup)",
    }
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            page = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError) as exc:
        raise SourceUnavailable("Mississippi contractor source could not be read") from exc
    if not page or "MSBOC Admin" not in page:
        raise SourceUnavailable("Mississippi contractor source returned an unexpected page")
    return page


def _search(query: str) -> list[dict[str, str]]:
    body = urlencode({"Keyword": query}).encode("ascii")
    page = _read_url(SOURCE_RESULTS_URL, data=body)
    parser = _ResultsParser()
    parser.feed(page)
    if not parser.rows and not re.search(r"no records", page, re.IGNORECASE):
        if "License Number" not in page or "Company Name" not in page:
            raise SourceUnavailable("Mississippi contractor search page changed unexpectedly")
    return parser.rows


def _detail(row: dict[str, str]) -> dict[str, str | None]:
    url = "https://search.msboc.us/" + row["detail_url"].lstrip("/")
    page = _read_url(url)
    plain = html.unescape(re.sub(r"<[^>]+>", " ", page))
    plain = " ".join(plain.split())

    def labeled_value(label: str) -> str | None:
        found = re.search(rf"\b{label}\s+([^ ]+)", plain, flags=re.IGNORECASE)
        return found.group(1).strip() if found else None

    status_match = re.search(r"\bStatus\s+([A-Za-z][A-Za-z ]*?)(?:\s+Class(?:ification|\(es\))|\s+Qualifying Name)", plain, re.I)
    status = " ".join(status_match.group(1).split()) if status_match else None
    expiration = labeled_value("Expiration")
    if expiration and not re.fullmatch(r"\d{2}/\d{2}/\d{4}", expiration):
        expiration = None
    return {
        "license_number": row["license_number"],
        "business_name": row["business_name"],
        "status": status,
        "expiration_date": datetime.strptime(expiration, "%m/%d/%Y").date().isoformat() if expiration else None,
        "source_url": url,
    }


def lookup_many(
    *, license_number: str | None = None, name: str | None = None, max_results: int = 1
) -> list[dict[str, object]]:
    """Look up one license number or a bounded set of business-name matches.

    Source/HTTP/schema failures are returned as ``uncertain`` and never as a clean
    no-match. Results preserve the board's status wording and expiration date.
    """
    if bool(license_number) == bool(name):
        raise ValueError("Provide exactly one of license_number or name")
    query = (license_number or name or "").strip()
    if not query or len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"Search text must be 1 to {MAX_QUERY_LENGTH} characters")
    if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= MAX_RESULTS:
        raise ValueError(f"max_results must be an integer from 1 to {MAX_RESULTS}")

    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    checked_date = checked_at[:10]
    try:
        search_term = re.sub(r"\D", "", query) if license_number else query
        rows = _search(search_term)
        if license_number:
            target = re.sub(r"[^A-Z0-9]", "", query.upper())
            rows = [
                row for row in rows
                if re.sub(r"[^A-Z0-9]", "", row["license_number"].upper()) == target
            ]
            rows = rows[:1]
        else:
            lowered = query.casefold()
            rows = [row for row in rows if lowered in row["business_name"].casefold()][:max_results]
        if not rows:
            return [{
                "outcome": f"no match found in {SOURCE_NAME} as of {checked_date}",
                "verification_state": "verified",
                "license_number": query if license_number else None,
                "status": None,
                "expiration_date": None,
                "source_url": SOURCE_SEARCH_URL,
                "checked_at": checked_at,
            }]
        results = []
        for row in rows:
            record = _detail(row)
            status = record["status"]
            expiration = record["expiration_date"]
            outcome = "match" if status and expiration else "uncertain — please check"
            results.append({
                "outcome": outcome,
                "verification_state": "verified" if outcome == "match" else "uncertain",
                **record,
                "checked_at": checked_at,
            })
        return results
    except (SourceUnavailable, ValueError, IndexError):
        return [{
            "outcome": "uncertain — please check",
            "verification_state": "unverifiable",
            "license_number": query if license_number else None,
            "status": None,
            "expiration_date": None,
            "source_url": SOURCE_SEARCH_URL,
            "checked_at": checked_at,
        }]


def lookup(
    *, license_number: str | None = None, name: str | None = None, max_results: int = 1
) -> dict[str, object]:
    """Convenience lookup returning the first record or no-match status."""
    return lookup_many(license_number=license_number, name=name, max_results=max_results)[0]


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
