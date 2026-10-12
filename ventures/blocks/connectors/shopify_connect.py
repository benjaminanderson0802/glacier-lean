"""One-time Shopify connect helper for Glacier (client-credentials apps).

You paste the app's Client ID and secret (hidden). Glacier saves them in its
keychain, fetches an Admin API token, and runs a read-only check.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from ventures.blocks.connectors.clients import ShopifyClient  # noqa: E402
from ventures.blocks.connectors.common import glacier_secret_writer  # noqa: E402


def main() -> None:
    print("Glacier <-> Shopify connect\n")
    domain = input("Store domain [glacier-test-cosmetics.myshopify.com]: ").strip() or "glacier-test-cosmetics.myshopify.com"
    client_id = input("Paste Client ID: ").strip()
    secret = getpass.getpass("Paste Client secret (hidden): ").strip()
    if not client_id or not secret:
        sys.exit("Client ID and secret are both needed.")
    if " " in client_id or len(client_id) < 20:
        sys.exit("That doesn't look like a Client ID (it should be one long code with no spaces). Run it again.")
    glacier_secret_writer("shopify_store_domain", domain)
    glacier_secret_writer("shopify_client_id", client_id)
    glacier_secret_writer("shopify_client_secret", secret)
    client = ShopifyClient(domain)
    result = client.test_connection()
    print(f"\nSaved all four Shopify values. Connected: {result}")


if __name__ == "__main__":
    main()
