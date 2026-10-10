#!/usr/bin/env python3
"""Loopback-only JSON API for the browser extension and local integrations."""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ventures.recall_checker import api_match_payload


class Handler(BaseHTTPRequestHandler):
    server_version = "GlacierRecallAPI/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # Do not log product identifiers or request bodies.
        super().log_message("%s", "recall API request")

    def _json(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin", "")
        if origin.startswith("chrome-extension://") and len(origin) < 200:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin", "")
        if not origin.startswith("chrome-extension://") or len(origin) >= 200:
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/api/health":
            self._json(200, {"ok": True, "service": "recall-checker"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/match":
            self._json(404, {"error": "not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 16_384:
                raise ValueError("request body must be between 1 and 16384 bytes")
            body = json.loads(self.rfile.read(size))
            self._json(200, api_match_payload(body))
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    server.daemon_threads = True
    print("Recall checker API listening on http://127.0.0.1:8765 (loopback only)")
    server.serve_forever()


if __name__ == "__main__":
    main()
