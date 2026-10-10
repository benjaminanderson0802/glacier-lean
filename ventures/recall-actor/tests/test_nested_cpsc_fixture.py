from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sources import normalize_cpsc  # noqa: E402
from src.matching import classify_matches  # noqa: E402


class CPSCNestedFixtureTests(unittest.TestCase):
    def test_documented_nested_product_collections_are_matched(self):
        payload = json.loads((ROOT / "tests" / "fixtures" / "cpsc_nested.json").read_text(encoding="utf-8"))
        recalls = normalize_cpsc(payload)
        self.assertEqual(recalls[0]["barcode_values"], ["012345678905"])
        self.assertEqual(recalls[0]["hazard"], "Fire hazard")
        self.assertEqual(classify_matches({"barcode": "012345678905"}, recalls)[0], "match")


if __name__ == "__main__":
    unittest.main()
