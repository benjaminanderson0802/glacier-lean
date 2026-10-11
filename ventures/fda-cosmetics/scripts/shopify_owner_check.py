"""Read-only Shopify connection check for the FDA cosmetics venture."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ventures.blocks.connectors import ConnectorError, ShopifyClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shop", help="Shopify *.myshopify.com domain")
    args = parser.parse_args(argv)
    client = None
    try:
        client = ShopifyClient(args.shop)
        connection = client.test_connection()
        products = client.get_products()
    except (ConnectorError, ValueError) as exc:
        print(json.dumps({"connected": False, "read_only": True, "error": str(exc)}, indent=2))
        return 1
    finally:
        if client is not None:
            client.close()

    print(json.dumps({
        "connected": True,
        "read_only": True,
        "shop": connection["shop"],
        "store_name": connection.get("name"),
        "products_read": len(products),
        "note": "Read only: this check requests shop metadata and products; it does not create or change Shopify records. Product details are not printed.",
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
