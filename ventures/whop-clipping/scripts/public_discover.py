"""Logged-out Content Rewards public campaign reader.

This module only fetches public HTML from contentrewards.com. It never calls
Whop or a Content Rewards API endpoint. ``joined_campaigns.txt`` is the owner's
manual record of campaigns joined on the site.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .interfaces import Campaign


BASE_URL = "https://contentrewards.com"
DISCOVER_URL = f"{BASE_URL}/c/discover"
CACHE_SECONDS = 60 * 60
USER_AGENT = "Glacier public campaign reader (contact: ben@andersoneducation.us)"


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.cards = []
        self.scripts = []
        self.links = []
        self.campaign_anchors = []
        self._script = None
        self._anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = {"tag": tag, "attrs": attrs, "text": [], "children": []}
        if self.stack:
            self.stack[-1]["children"].append(node)
        if tag == "article" or "data-campaign-card" in attrs:
            self.cards.append(node)
        if tag == "script":
            self._script = []
        if tag == "a":
            in_main = any(parent["tag"] == "main" or parent["attrs"].get("role") == "main"
                          for parent in self.stack)
            self._anchor = [attrs.get("href", ""), [], in_main]
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append("".join(self._script))
            self._script = None
        if tag == "a" and self._anchor is not None:
            href, text, in_main = self._anchor
            label = " ".join(text).strip()
            if in_main:
                self.links.append((href, label))
            if _campaign_id_from_url(urljoin(BASE_URL, href)):
                self.campaign_anchors.append((href, label))
            self._anchor = None
        for idx in range(len(self.stack) - 1, -1, -1):
            if self.stack[idx]["tag"] == tag:
                del self.stack[idx:]
                break

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)
        if self._anchor is not None and data.strip():
            self._anchor[1].append(data.strip())
        if self.stack:
            self.stack[-1]["text"].append(data)


def _flatten(node):
    return " ".join([*node["text"], *(_flatten(child) for child in node["children"])])


def _split_values(value):
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, dict):
        return _split_values(list(value.values()))
    if value is None:
        return []
    return [item.strip().lower() for item in re.split(r"[,|]", str(value)) if item.strip()]


def _float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
    return float(match.group(0).replace(",", "")) if match else None


def _money(raw, *, cents=False):
    value = _float(raw)
    return value / 100 if value is not None and cents else value


def _campaign_id_from_url(url):
    match = re.search(r"/c/campaigns/([^/?#]+)", urlparse(url).path)
    return match.group(1) if match else ""


def _compact_amount(raw):
    match = re.search(r"(-?\d[\d,]*(?:\.\d+)?)\s*([kmb])?", str(raw), re.I)
    if not match:
        return None
    amount = float(match.group(1).replace(",", ""))
    scale = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(
        (match.group(2) or "").lower(), 1
    )
    return amount * scale


def _anchor_card(href, text):
    campaign_id = _campaign_id_from_url(urljoin(BASE_URL, href))
    if not campaign_id:
        return None
    # Live cards render as: organization · age title $used / $budget
    # submissions $cpm /1K. Keep this as a fallback for markup without data.
    metrics = re.search(
        r"\$\s*(?P<used>[\d,.]+\s*[kmb]?)\s*/\s*\$\s*"
        r"(?P<budget>[\d,.]+\s*[kmb]?)\s+(?P<submissions>[\d,.]+)\s+"
        r"\$\s*(?P<cpm>[\d,.]+(?:\s*[kmb])?)\s*/\s*1k\b",
        text,
        re.I,
    )
    if not metrics:
        return None
    prefix = text[:metrics.start()].strip()
    title_match = re.search(r"(?:Â)?·\s*\d+\s*[a-z]+\s*(.+?)\s*$", prefix, re.I)
    name = title_match.group(1).strip() if title_match else prefix
    if not name:
        return None
    return _normalize_card({
        "id": campaign_id,
        "name": name,
        "cpm_usd": _compact_amount(metrics.group("cpm")),
        "budget_used_usd": _compact_amount(metrics.group("used")),
        "budget_total_usd": _compact_amount(metrics.group("budget")),
    }, href)


class _PublicRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        PublicDiscoverScout._validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _normalize_card(data, url=""):
    campaign_id = str(data.get("id") or _campaign_id_from_url(url))
    if not campaign_id:
        return None
    name = data.get("name") or data.get("title") or data.get("campaignName") or ""
    href = url or data.get("url") or data.get("href") or f"/c/campaigns/{campaign_id}"
    full_url = urljoin(BASE_URL, href)
    # Discover's public SSR card data exposes USD values with Raw suffixes and
    # a human rate label; campaign detail data exposes cents and payoutModel.
    cpm = _money(data.get("cpm_usd", data.get("cpm")))
    if cpm is None:
        cpm = _money(data.get("cpmMaxRateCents"), cents=True)
    if cpm is None:
        cpm = _money(data.get("ratePer1kLabel"))
    configuration = data.get("configuration") or {}
    payout_model = data.get("payoutModel") or configuration.get("payoutModel") or []
    if cpm is None:
        rate = payout_model
        rates = [_money(item.get("rate"), cents=True) for item in rate if isinstance(item, dict)]
        rates = [item for item in rates if item is not None]
        cpm = max(rates) if rates else 0.0
    budget_total = _money(data.get("budget_total_usd", data.get("budgetTotalRaw")))
    if budget_total is None:
        budget_total = _money(data.get("budgetCents", data.get("budget", configuration.get("budget"))), cents=True)
    budget_used = _money(data.get("budget_used_usd", data.get("budgetSpentRaw")))
    if budget_used is None:
        metrics = data.get("metrics") or {}
        budget_used = _money(metrics.get("budgetSpentCents"), cents=True)
    budget_left = _money(data.get("availableBudgetRaw"))
    if budget_left is None and budget_total is not None and budget_used is not None:
        budget_left = max(0.0, budget_total - budget_used)
    if budget_left is None and budget_total is not None:
        progress = _float(data.get("progressPercentage"))
        if progress is not None:
            budget_left = max(0.0, budget_total * (100 - progress) / 100)
    platforms = data.get("platforms") or []
    if not platforms:
        platforms = [item.get("platform") for item in payout_model if isinstance(item, dict)]
    return {
        "id": campaign_id,
        "name": str(name).strip(),
        "url": full_url,
        "cpm_usd": cpm or 0.0,
        "budget_used_usd": budget_used,
        "budget_total_usd": budget_total,
        "budget_left_usd": budget_left,
        "platforms": _split_values(platforms),
        "rules_text": str(data.get("rules_text") or data.get("rules") or data.get("description") or ""),
        "source_links": [],
    }


def _next_data_objects(scripts):
    """Decode JSON string payloads React streams in public page HTML."""
    decoder = json.JSONDecoder()
    for script in scripts:
        cursor = 0
        while True:
            marker = script.find("push([1,", cursor)
            if marker < 0:
                break
            start = marker + len("push([1,")
            try:
                payload, end = decoder.raw_decode(script, start)
            except json.JSONDecodeError:
                cursor = start
                continue
            cursor = end
            if not isinstance(payload, str):
                continue
            for key in ('"initialPage":', '"data":'):
                offset = 0
                while (index := payload.find(key, offset)) >= 0:
                    start_obj = index + len(key)
                    while start_obj < len(payload) and payload[start_obj].isspace():
                        start_obj += 1
                    try:
                        value, _ = decoder.raw_decode(payload, start_obj)
                    except json.JSONDecodeError:
                        offset = start_obj
                        continue
                    offset = start_obj + 1
                    if isinstance(value, (dict, list)):
                        yield value
            # Some versions serialize JSON-LD outside React's stream.
    for script in scripts:
        try:
            value = json.loads(script)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(value, (dict, list)):
            yield value


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _card_objects(scripts):
    seen = set()
    for root in _next_data_objects(scripts):
        for item in _walk(root):
            if (item.get("id") and (item.get("title") or item.get("name"))
                    and any(key in item for key in ("type", "payoutModel", "budgetTotalRaw", "budgetCents"))):
                key = str(item["id"])
                if key not in seen:
                    seen.add(key)
                    yield item


def _element_card(card):
    attrs = card["attrs"]
    data = {
        "id": attrs.get("data-campaign-id"),
        "cpm_usd": attrs.get("data-cpm"),
        "budget_used_usd": attrs.get("data-budget-used"),
        "budget_total_usd": attrs.get("data-budget-total"),
        "platforms": attrs.get("data-platforms"),
        "rules_text": attrs.get("data-rules"),
    }
    for item in _walk(card):
        if "attrs" not in item:
            continue
        href = item["attrs"].get("href", "")
        if _campaign_id_from_url(urljoin(BASE_URL, href)):
            data["url"] = href
            data["id"] = data.get("id") or _campaign_id_from_url(href)
            data["name"] = _flatten(item).strip()
            break
    if not data.get("name"):
        data["name"] = _flatten(card).strip()
    return _normalize_card(data, data.get("url", ""))


def parse_campaign_cards(html):
    parser = _PageParser()
    parser.feed(html)
    found = {}
    for item in _card_objects(parser.scripts):
        card = _normalize_card(item)
        if card:
            found[card["id"]] = card
    for item in parser.cards:
        card = _element_card(item)
        if card:
            found.setdefault(card["id"], card)
    for href, text in parser.campaign_anchors:
        card = _anchor_card(href, text)
        if card:
            found.setdefault(card["id"], card)
    # Campaign list pages may expose JSON-LD item lists.
    for root in _next_data_objects(parser.scripts):
        for item in _walk(root):
            if item.get("@type") == "Campaign" or item.get("@type") == "Offer":
                card = _normalize_card(item)
                if card:
                    found.setdefault(card["id"], card)
    return list(found.values())


def _details_objects(scripts):
    for root in _next_data_objects(scripts):
        for item in _walk(root):
            if item.get("id") and any(key in item for key in ("description", "payoutModel", "references", "requirements")):
                yield item


def _extract_sources(value):
    links = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in {"references", "referencematerials", "sourcelinks", "sourcecontent", "sourcecontentlinks", "assets"}:
                values = child if isinstance(child, list) else [child]
                for source in values:
                    if isinstance(source, str) and source.startswith(("http://", "https://")):
                        links.append({"url": source, "label": ""})
                    elif isinstance(source, dict):
                        url = source.get("url") or source.get("href") or source.get("link")
                        if url and str(url).startswith(("http://", "https://")):
                            links.append({"url": str(url), "label": str(source.get("label") or source.get("title") or source.get("name") or "")})
            else:
                links.extend(_extract_sources(child))
    elif isinstance(value, list):
        for child in value:
            links.extend(_extract_sources(child))
    unique = {}
    for link in links:
        unique[link["url"]] = link
    return list(unique.values())


def _rules_text(value):
    parts = []
    rule_keys = {"rules", "rules_text", "requirements", "creatorrequirements", "contentrules", "description"}
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in rule_keys:
                if isinstance(child, str) and child.strip():
                    parts.append(child.strip())
                elif isinstance(child, list):
                    parts.extend(_rules_text(child).splitlines())
                elif isinstance(child, dict):
                    for row in _walk(child):
                        for text_key in ("text", "description", "title", "label", "value"):
                            text = row.get(text_key)
                            if isinstance(text, str) and text.strip():
                                parts.append(text.strip())
            else:
                parts.extend(_rules_text(child).splitlines())
    elif isinstance(value, list):
        for child in value:
            parts.extend(_rules_text(child).splitlines())
    return "\n".join(dict.fromkeys(part for part in parts if part))


def parse_campaign_detail(html, card=None):
    parser = _PageParser()
    parser.feed(html)
    base = dict(card or {})
    data = None
    for item in _details_objects(parser.scripts):
        if not base.get("id") or str(item.get("id")) == str(base["id"]):
            data = item
            break
    for script in parser.scripts:
        if "application/ld+json" not in script and not script.lstrip().startswith("{"):
            continue
        try:
            value = json.loads(script)
        except json.JSONDecodeError:
            continue
        candidates = [*(_walk(value))]
        data = next((item for item in candidates if item.get("@type") == "Campaign"), data)
    if data is None:
        data = {}
    merged = {**base, **data}
    result = _normalize_card(merged, base.get("url", ""))
    if not result["name"]:
        result["name"] = str(base.get("name") or "").strip()
    if result["cpm_usd"] == 0 and base.get("cpm_usd") is not None:
        result["cpm_usd"] = base["cpm_usd"]
    if result["budget_total_usd"] is None:
        result["budget_total_usd"] = base.get("budget_total_usd")
    if result["budget_used_usd"] is None:
        result["budget_used_usd"] = base.get("budget_used_usd")
    if result["budget_left_usd"] is None:
        result["budget_left_usd"] = base.get("budget_left_usd")
    if not result["platforms"]:
        result["platforms"] = list(base.get("platforms", []))
    result["rules_text"] = _rules_text(data) or result["rules_text"] or str(base.get("rules_text", ""))
    result["source_links"] = _extract_sources(data)
    for href, label in parser.links:
        absolute = urljoin(result["url"], href)
        parsed = urlparse(absolute)
        if parsed.scheme in {"http", "https"} and parsed.netloc.lower() != "contentrewards.com":
            result["source_links"].append({"url": absolute, "label": label})
    result["source_links"] = list({link["url"]: link for link in result["source_links"]}.values())
    result["requires_editing"] = data.get("requiresEditing") if "requiresEditing" in data else None
    result["min_payout_usd"] = _money(data.get("cpmMinRateCents"), cents=True)
    result["max_payout_usd"] = _money(data.get("cpmMaxRateCents"), cents=True)
    return result


class PublicDiscoverScout:
    """Read public campaign HTML, ranking only URLs the owner recorded as joined."""
    user_agent = USER_AGENT

    def __init__(self, config=None, *, fetcher=None, clock=time.time):
        config = config or {}
        self.home = Path(config["clip_home"]) if config.get("clip_home") else Path.home() / ".glacier/ventures/whop-clipping"
        self.cache_dir = self.home / "public-discover-cache"
        self.joined_path = self.home / "joined_campaigns.txt"
        self.fetcher = fetcher or self._fetch_public_html
        self.clock = clock
        self._cards = None
        self._by_id = None
        self._details = {}

    @staticmethod
    def _validate_url(url):
        parsed = urlparse(urljoin(BASE_URL, str(url)))
        if parsed.scheme != "https" or parsed.netloc != "contentrewards.com":
            raise ValueError("Public campaign URLs must stay on contentrewards.com")
        if parsed.path == "/api" or parsed.path.startswith("/api/"):
            raise ValueError("/api/ is disallowed by contentrewards.com/robots.txt")
        return parsed.geturl()

    def _fetch_public_html(self, url):
        req = Request(url, headers={"User-Agent": self.user_agent, "Accept": "text/html"})
        opener = build_opener(_PublicRedirectHandler())
        with opener.open(req, timeout=30) as response:
            final_url = self._validate_url(response.geturl())
            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                raise ValueError(f"Expected a public HTML page, received {content_type!r}")
            return response.read().decode("utf-8", "replace")

    def _cached_page(self, url):
        url = self._validate_url(url)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            record = None
        if record and self.clock() - float(record.get("fetched_at", 0)) < CACHE_SECONDS:
            return record["html"]
        html = self.fetcher(url)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps({"url": url, "fetched_at": self.clock(), "html": html}), encoding="utf-8")
        temp.replace(path)
        return html

    def _discover_cards(self):
        if self._cards is None:
            html = self._cached_page(DISCOVER_URL)
            self._cards = parse_campaign_cards(html)
            self._by_id = {card["id"]: card for card in self._cards}
        return self._cards

    def _detail(self, card):
        if card["id"] not in self._details:
            html = self._cached_page(card["url"])
            self._details[card["id"]] = parse_campaign_detail(html, card)
        return self._details[card["id"]]

    def _joined_campaign_ids(self):
        if not self.joined_path.exists():
            return set()
        campaign_ids = set()
        for line in self.joined_path.read_text(encoding="utf-8").splitlines():
            value = line.split("#", 1)[0].strip()
            if not value:
                continue
            parsed = urlparse(value)
            campaign_id = _campaign_id_from_url(value) if parsed.scheme or "/" in value else value
            if campaign_id:
                campaign_ids.add(campaign_id.casefold())
        return campaign_ids

    def list_campaigns(self):
        cards = self._discover_cards()
        joined = self._joined_campaign_ids()
        selected = [card for card in cards if card["id"].casefold() in joined]
        return [_campaign_contract(self._detail(card)) for card in selected]

    @property
    def joined_campaign_ids(self):
        return {campaign.id for campaign in self.list_campaigns()}

    def join_suggestions(self, limit=10):
        joined = self._joined_campaign_ids()
        candidates = []
        for card in self._discover_cards():
            platforms = {str(value).lower().replace(" ", "_") for value in card["platforms"]}
            rules = card["rules_text"].lower()
            allowed_line = re.search(
                r"(?:allowed|eligible) platforms?\s*[:=]\s*([^\n.]+)",
                card["rules_text"], re.I,
            )
            youtube_allowed = bool(platforms & {"youtube", "youtube_shorts", "shorts"})
            youtube_prohibited = bool(re.search(
                r"(?:youtube(?: shorts)?).{0,35}(?:not allowed|prohibited|forbidden|excluded)|"
                r"(?:no|do not use|don't use)\s+youtube", rules,
            ))
            if allowed_line and not re.search(r"youtube|shorts", allowed_line.group(1), re.I):
                youtube_prohibited = True
            if (card["id"].casefold() in joined or card["cpm_usd"] <= 0
                    or card["budget_left_usd"] is None or card["budget_left_usd"] <= 0
                    or not youtube_allowed or youtube_prohibited):
                continue
            candidates.append(card)
        candidates.sort(key=lambda row: (row["cpm_usd"], row["budget_left_usd"] or 0), reverse=True)
        suggestions = [self._detail(card) for card in candidates[:max(0, int(limit))]]
        self.home.mkdir(parents=True, exist_ok=True)
        path = self.home / "join_suggestions.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps({"updated_at": self.clock(), "campaigns": suggestions}, indent=2), encoding="utf-8")
        temp.replace(path)
        return suggestions


def _campaign_contract(row):
    """Convert public-page data into the stable campaign interface."""
    fields = Campaign.__dataclass_fields__
    values = {name: row[name] for name in fields if name in row}
    return Campaign(**values)


__all__ = ["PublicDiscoverScout", "parse_campaign_cards", "parse_campaign_detail"]
