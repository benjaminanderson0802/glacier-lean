"""Per-install access token for the local engine.

Every /api request and the live-events WebSocket must carry this token, so other programs or
users on the same computer cannot drive Glacier. The desktop app reads the token file and hands
it to the screen; command-line tools read it from the same file.

- File: <GLACIER_HOME>/.engine-token, created on first start with 32 random bytes (hex).
  POSIX: mode 0600. Windows: the file lives in the user's own profile folder, whose default ACL
  already limits it to that user (and administrators).
- GLACIER_TOKEN in the environment overrides the file (tests, CI, scripted setups).
"""
import hmac
import os
import secrets

TOKEN_FILE = ".engine-token"


def _home() -> str:
    return os.environ.get("GLACIER_HOME") or os.path.join(os.path.expanduser("~"), ".glacier")


def token_path() -> str:
    return os.path.join(_home(), TOKEN_FILE)


def get_token() -> str:
    """Return the install token, creating the token file the first time."""
    configured = os.environ.get("GLACIER_TOKEN", "").strip()
    if configured:
        return configured
    path = token_path()
    try:
        with open(path, encoding="utf-8") as handle:
            existing = handle.read().strip()
        if existing:
            return existing
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    value = secrets.token_hex(32)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value)
    if os.name != "nt":
        os.chmod(path, 0o600)
    return value


def matches(candidate: str | None) -> bool:
    return bool(candidate) and hmac.compare_digest(candidate.encode(), get_token().encode())


def from_headers_or_protocol(headers: dict[str, str]) -> str | None:
    """Bearer header or the Glacier events WebSocket subprotocol credential."""
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    protocols = [value.strip() for value in headers.get("sec-websocket-protocol", "").split(",")]
    if "glacier-events" in protocols:
        return next((value for value in protocols if value and value != "glacier-events"), None)
    return None
