from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sources import request_json, SOURCE_URLS  # noqa: E402


@unittest.skipUnless(os.getenv("RUN_RECALL_LIVE_CANARY") == "1", "set RUN_RECALL_LIVE_CANARY=1 to call the public CPSC API")
class LiveRecallCanaryTests(unittest.TestCase):
    def test_cpsc_public_endpoint_returns_json(self):
        payload = request_json(SOURCE_URLS["CPSC"], {"format": "json", "RecallNumber": "24-123"})
        self.assertIsInstance(payload, list)


if __name__ == "__main__":
    unittest.main()
