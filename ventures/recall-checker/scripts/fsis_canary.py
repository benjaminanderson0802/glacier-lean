#!/usr/bin/env python3
"""Canary the documented FSIS API and its official RSS alternatives.

This deliberately does not impersonate a browser. A reachable but partial RSS
feed is reported as partial coverage and cannot authorize a clean result.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ventures.blocks.feeds import registry
from ventures.blocks.feeds.core import _records_and_total
from fsis_feed import canonical_fsis_records

FSIS_RSS_URL = "https://www.fsis.usda.gov/RSS/usdarss.xml"
# CDC describes this HHS feed as combined food-safety news. It is useful as a
# discovery fallback, but it is not itself a complete FSIS recall snapshot.
CDC_FOOD_SAFETY_RSS_URL = "https://www2c.cdc.gov/podcasts/createrss.asp?c=146"
USER_AGENT = "Glacier public-data client"
TIMEOUT_SECONDS = 20


def _get(url: str, opener: Callable = urllib.request.urlopen) -> tuple[int, bytes, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json, application/rss+xml, application/xml"},
    )
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers.get("Content-Type", "")


def _feed_items(raw: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(raw)
    if root.tag.rsplit("}", 1)[-1].lower() != "rss":
        raise ValueError("RSS alternative did not return an RSS document")
    items = []
    for item in root.findall(".//item"):
        items.append({
            "title": item.findtext("title", default="").strip(),
            "guid": item.findtext("guid", default="").strip(),
            "link": item.findtext("link", default="").strip(),
            "pub_date": item.findtext("pubDate", default="").strip(),
        })
    return items


def _is_fsis_url(value: str) -> bool:
    hostname = (urlparse(value).hostname or "").lower()
    return hostname == "fsis.usda.gov" or hostname.endswith(".fsis.usda.gov")


def probe_official_sources(opener: Callable = urllib.request.urlopen) -> dict:
    """Return a conservative availability record; partial feeds never mean complete."""
    api_url = registry()["fsis_recalls"]["url"]
    api: dict = {"url": api_url}
    api_records: list[dict] = []
    status, raw, content_type = _get(api_url, opener)
    api.update({"http_status": status, "content_type": content_type})
    if status == 200:
        try:
            api_records, _ = _records_and_total(json.loads(raw.decode("utf-8-sig")))
            id_fields = registry()["fsis_recalls"]["id_fields"]
            canary_count = sum(any(record.get(field) not in (None, "") for field in id_fields) for record in api_records)
            canonical_records = canonical_fsis_records(api_records)
            api["records"] = len(api_records)
            api["identifier_canary_records"] = canary_count
            api["unique_recall_records"] = len(canonical_records)
            api["duplicate_or_translation_rows_removed"] = len(api_records) - len(canonical_records)
            api["sample_record_fields"] = sorted(api_records[0])[:40] if api_records else []
            api["usable"] = bool(api_records and canary_count)
            if not api["usable"]:
                api["error"] = "HTTP 200 response lacked FSIS recall records with a recognized identifier"
        except (UnicodeError, ValueError, TypeError, json.JSONDecodeError) as error:
            api.update({"usable": False, "error": f"invalid official JSON response: {type(error).__name__}: {error}"})
    else:
        api.update({"usable": False, "error": f"official API returned HTTP {status}"})

    rss: dict = {"fsis_url": FSIS_RSS_URL, "cdc_combined_url": CDC_FOOD_SAFETY_RSS_URL}
    rss_items: list[dict[str, str]] = []
    for label, url in (("fsis", FSIS_RSS_URL), ("cdc_combined", CDC_FOOD_SAFETY_RSS_URL)):
        code, body, media_type = _get(url, opener)
        source = {"url": url, "http_status": code, "content_type": media_type, "usable_fsis_records": 0}
        if code == 200:
            try:
                items = _feed_items(body)
                matched = [item for item in items if _is_fsis_url(item["guid"]) or _is_fsis_url(item["link"])]
                source.update({"items": len(items), "usable_fsis_records": len(matched), "items_sampled": True})
                if matched:
                    rss_items.extend(matched)
            except (ET.ParseError, ValueError) as error:
                source["error"] = f"invalid official RSS response: {type(error).__name__}: {error}"
        else:
            source["error"] = f"official feed returned HTTP {code}"
        rss[label] = source

    if api.get("usable"):
        status_label = "available"
        explanation = "Documented FSIS API returned recall records with identifiers."
    elif rss_items:
        status_label = "partial"
        explanation = "Official RSS exposed some FSIS notices, but RSS is not verified as a complete recall snapshot; unmatched items remain uncertain."
    else:
        status_label = "unavailable"
        explanation = "No probed official source returned verifiable FSIS recall records; unmatched items remain uncertain."
    return {
        "source": "FSIS",
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status_label,
        "complete_snapshot": bool(api.get("usable")),
        "api": api,
        "rss": rss,
        "usable_fsis_rss_records": len(rss_items),
        "explanation": explanation,
    }


def main() -> int:
    result = probe_official_sources()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["complete_snapshot"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
