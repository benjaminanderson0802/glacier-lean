"""Authorize the ten linked YouTube channels using Google's official OAuth flow."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

if __package__:
    from .channels import CHANNEL_HANDLES
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.channels import CHANNEL_HANDLES


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def clip_home(home=None):
    return Path(home or os.environ.get("CLIP_HOME", Path.home() / ".glacier/ventures/whop-clipping"))


def channel_identity(credentials, *, service=None):
    """Return the channel handle from a consented token without exposing credentials."""
    youtube = service or build("youtube", "v3", credentials=credentials, cache_discovery=False)
    response = youtube.channels().list(part="id,snippet", mine=True, maxResults=5).execute()
    items = response.get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"Expected one channel for this OAuth selection; received {len(items)}")
    item = items[0]
    custom_url = str(item.get("snippet", {}).get("customUrl", "")).strip()
    if not custom_url.startswith("@"):
        custom_url = "@" + custom_url.lstrip("@") if custom_url else ""
    return {"id": str(item.get("id", "")), "handle": custom_url,
            "title": str(item.get("snippet", {}).get("title", ""))}


def _token_file(tokens_dir: Path, handle: str):
    return tokens_dir / f"{handle.lower()}.json"


def authorize_all(*, home=None, handles=None, flow_factory=InstalledAppFlow.from_client_secrets_file,
                  service_factory=None, output_fn=print):
    root = clip_home(home)
    tokens_dir = root / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    client_secret = tokens_dir / "client_secret.json"
    if not client_secret.is_file():
        raise FileNotFoundError(f"Google OAuth client file is required at {client_secret}")
    requested = list(handles or CHANNEL_HANDLES)
    remaining = list(requested)
    # Re-consent for each missing handle; already-present tokens are reported as complete.
    for handle in list(remaining):
        if _token_file(tokens_dir, handle).is_file():
            output_fn(f"Already authorized: {handle}")
            remaining.remove(handle)
    while remaining:
        output_fn("Channels still needing authorization: " + ", ".join(remaining))
        target = remaining[0]
        output_fn(f"Choose the Google/brand account for {target} in Google's account chooser.")
        flow = flow_factory(str(client_secret), scopes=SCOPES)
        credentials = flow.run_local_server(port=0, open_browser=True)
        identity = channel_identity(credentials, service=(service_factory(credentials)
                                                           if service_factory else None))
        actual_handle = identity["handle"].casefold()
        expected = target.casefold()
        if actual_handle != expected:
            output_fn(f"Selected {identity['title']} ({identity['handle'] or identity['id']}); expected {target}. "
                      "No token was saved. Restart consent and choose the matching channel.")
            continue
        token_path = _token_file(tokens_dir, target)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        try:
            token_path.chmod(0o600)
        except OSError:
            pass
        remaining.remove(target)
        output_fn(f"Authorized {target}. Remaining: {len(remaining)}")
    output_fn("All configured YouTube channels are authorized.")
    return list(requested)


def main():
    authorize_all()


if __name__ == "__main__":
    main()
