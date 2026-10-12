"""One-time Jobber connect helper for Glacier.

You type the app ID and secret yourself (hidden), approve Glacier in Jobber,
then paste back the address you land on. Tokens go straight into Glacier's
keychain; nothing is printed or written to files.
"""
from __future__ import annotations

import getpass
import secrets as pysecrets
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import httpx  # noqa: E402

from ventures.blocks.connectors.clients import JobberClient  # noqa: E402
from ventures.blocks.connectors.common import glacier_secret, glacier_secret_writer  # noqa: E402

REDIRECT = "https://example.com/glacier/jobber-callback"


def ask(name: str, label: str, hidden: bool) -> str:
    saved = glacier_secret(name)
    if saved:
        keep = input(f"{label} is already saved. Press Enter to keep it, or type N to replace: ").strip().lower()
        if keep != "n":
            return saved
    value = (getpass.getpass if hidden else input)(f"Paste {label}: ").strip()
    if not value:
        sys.exit(f"No {label} entered; stopping.")
    glacier_secret_writer(name, value)
    return value


def main() -> None:
    print("Glacier <-> Jobber connect\n")
    client_id = ask("jobber_client_id", "Jobber app ID (Client ID)", hidden=False)
    client_secret = ask("jobber_client_secret", "Jobber app secret (Client Secret)", hidden=True)
    state = pysecrets.token_urlsafe(16)
    url = "https://api.getjobber.com/api/oauth/authorize?" + urlencode(
        {"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT, "state": state})
    print("\nA browser tab will open. Log in to the TEST Jobber account (Glacier Test HVAC) and click Allow.")
    print("You'll land on an example.com page. Copy that page's full address from the address bar.\n")
    webbrowser.open(url)
    landed = input("Paste the example.com address here: ").strip()
    query = parse_qs(urlparse(landed).query)
    if query.get("state", [""])[0] != state:
        sys.exit("That address doesn't match this connect attempt. Run the helper again.")
    code = query.get("code", [""])[0]
    if not code:
        sys.exit("No approval code found in that address. Run the helper again.")
    resp = httpx.post("https://api.getjobber.com/api/oauth/token", data={
        "client_id": client_id, "client_secret": client_secret, "grant_type": "authorization_code",
        "code": code, "redirect_uri": REDIRECT}, timeout=30)
    if resp.status_code != 200:
        sys.exit(f"Jobber refused the exchange (HTTP {resp.status_code}). Check the app ID/secret and try again.")
    payload = resp.json()
    glacier_secret_writer("jobber_access_token", payload["access_token"])
    glacier_secret_writer("jobber_refresh_token", payload["refresh_token"])
    print("\nSaved all four Jobber values in Glacier's keychain. Running the read-only check...")
    result = JobberClient().test_connection()
    print(f"Connected to Jobber account: {result['account']}")
    print(f"Jobs readable: {len(JobberClient().get_jobs(page_size=20, max_pages=1))}")


if __name__ == "__main__":
    main()
