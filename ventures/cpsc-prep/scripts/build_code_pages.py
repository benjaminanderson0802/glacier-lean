"""Generate one public information page per current flagged code and rule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpsc_prep import load_blocks


TEMPLATE = """<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">
<title>Check CPSC filing data for {{tariff_code}}</title>
<main><p>CPSC import data preparation</p>
<h1>Is tariff code {{tariff_code}} flagged?</h1>
<p>Source: {{source_url}}. Checked {{checked_at}}.</p>
<p>This page is an independent preparation service, not a government notice or legal advice.
Confirm requirements with your importer or licensed customs broker.</p>
<p>Rule references present in the current CPSC feed: {{rule_codes}}</p></main></html>
"""


def current_objects() -> list[dict]:
    _, _, feeds = load_blocks()
    feeds.sync("cpsc_flagged_tariff_codes")
    feeds.sync("cpsc_rule_codes")
    code_rows = feeds.query("cpsc_flagged_tariff_codes")
    rule_rows = feeds.query("cpsc_rule_codes")
    objects = []
    for code in code_rows:
        tariff_code = code.get("tariff_code", code.get("code"))
        if not tariff_code:
            continue
        source_url = code.get("source_url")
        checked_at = code.get("checked_at")
        if not source_url or not checked_at:
            raise RuntimeError(f"CPSC feed record for {tariff_code} is missing source_url or checked_at")
        linked = [row for row in rule_rows if row.get("tariff_code") == tariff_code]
        objects.append({
            "tariff_code": str(tariff_code),
            "source_url": str(source_url),
            "checked_at": str(checked_at),
            "rule_codes": ", ".join(str(row.get("code", row.get("rule_code", ""))) for row in linked if row.get("code", row.get("rule_code"))),
        })
    return objects


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("code-pages-preview.json"))
    parser.add_argument("--publish-from", type=Path)
    args = parser.parse_args()
    if args.publish_from:
        objects = json.loads(args.publish_from.read_text(encoding="utf-8"))
    else:
        objects = current_objects()
    if args.preview:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(objects, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"prepared {len(objects)} CPSC code-page previews at {args.out}; nothing published")
        return 0
    from ventures.blocks.mail import landing_pages
    site_dir = landing_pages(objects, TEMPLATE)
    print(site_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
