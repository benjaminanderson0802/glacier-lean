"""Benchmarks start their own engine: give it a fresh install token and attach it to local calls.

Import this module before making requests. A case can opt out with the request header
X-Glacier-No-Token: 1 (used by security cases that check calls without the token are refused).
"""
import secrets
import urllib.request

TOKEN = secrets.token_hex(32)
_LOCAL = ("127.0.0.1", "localhost")


def server_env(env: dict) -> dict:
    out = dict(env)
    out["GLACIER_TOKEN"] = TOKEN
    return out


class _AddToken(urllib.request.BaseHandler):
    handler_order = 100

    def http_request(self, req):
        skip = req.get_header("X-glacier-no-token")
        if skip is not None:
            req.remove_header("X-glacier-no-token")
        elif req.host.split(":")[0] in _LOCAL and not req.has_header("Authorization"):
            req.add_unredirected_header("Authorization", f"Bearer {TOKEN}")
        return req

    https_request = http_request


urllib.request.install_opener(urllib.request.build_opener(_AddToken()))
