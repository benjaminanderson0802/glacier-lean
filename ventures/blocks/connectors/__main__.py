"""One-command owner connection checks: python -m ventures.blocks.connectors PLATFORM."""

from __future__ import annotations

import argparse
import json
import sys

from . import ApifyClient, ConnectorError, JobberClient, ShipStationClient, ShopifyClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a read-only connection using credentials saved in Glacier.")
    parser.add_argument("platform", choices=("jobber", "shipstation", "shopify", "apify"))
    parser.add_argument("--shop", help="Shopify *.myshopify.com store domain")
    args = parser.parse_args(argv)
    if args.platform == "jobber":
        client = JobberClient()
    elif args.platform == "shipstation":
        client = ShipStationClient()
    elif args.platform == "shopify":
        if not args.shop:
            parser.error("shopify requires --shop STORE.myshopify.com")
        client = ShopifyClient(args.shop)
    else:
        client = ApifyClient()
    try:
        print(json.dumps(client.test_connection(), sort_keys=True))
        return 0
    except ConnectorError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
