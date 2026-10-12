from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from ventures.blocks.mail.engine import _proof_browser

SCRIPT = Path(__file__).parents[1] / "scripts" / "osha_filing.py"
SPEC = importlib.util.spec_from_file_location("osha_filing_release_helpers", SCRIPT)
assert SPEC and SPEC.loader
OSHA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OSHA)


class OshaReleaseGateHelperTests(unittest.TestCase):
    def test_deadline_digest_uses_next_filing_year_after_posting_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GLACIER_HOME": tmp}):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(OSHA.main(["deadlines", "--as-of", "2026-10-10"]), 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["customer_actions"][0]["window"], "2027-01-02 through 2027-03-02")
        self.assertEqual(report["customer_actions"][0]["due"], "2027-03-02")
        self.assertEqual(report["customer_actions"][1]["window"], "2027-02-01 through 2027-04-30")

    def test_deadline_digest_keeps_current_filing_year_during_opening_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GLACIER_HOME": tmp}):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(OSHA.main(["deadlines", "--as-of", "2027-02-15"]), 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["customer_actions"][0]["window"], "2027-01-02 through 2027-03-02")
        self.assertEqual(report["customer_actions"][0]["due"], "2027-03-02")
        self.assertEqual(report["customer_actions"][1]["window"], "2027-02-01 through 2027-04-30")

    def test_public_ita_size_code_uses_peak_size_instead_of_annual_average(self) -> None:
        rows = [
            {"establishment_id": "large", "size": "3", "annual_average_employees": "42", "naics_code": "332710"},
            {"establishment_id": "small", "size": "21", "annual_average_employees": "250", "naics_code": "5412"},
        ]
        result = OSHA.eligible_prospects(as_of=date(2027, 1, 3), records=rows)
        self.assertEqual([row["establishment_id"] for row in result["prospects"]], ["large"])
        self.assertEqual(result["excluded"][0]["establishment_id"], "small")

    def test_local_csv_mode_records_row_count_and_identifier_canary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GLACIER_HOME": tmp}):
            source = Path(tmp) / "synthetic-ita-summary-shape.csv"
            source.write_text(
                "establishment_id,size,annual_average_employees,naics_code,establishment_name\n"
                "synthetic-1,3,42,332710,Example Manufacturing\n",
                encoding="utf-8",
            )
            output = Path(tmp) / "selected.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(OSHA.main(["prospects", "--source-csv", str(source), "--as-of", "2027-01-03", "--output", str(output)]), 0)
            report = json.loads(stdout.getvalue())
            status = json.loads((output.parent / "prospect-status.json").read_text(encoding="utf-8"))
        self.assertEqual(report["source_mode"], "local_csv")
        self.assertEqual(report["source_row_count"], 1)
        self.assertTrue(report["source_canary_present"])
        self.assertEqual(status["source_row_count"], 1)
        self.assertTrue(status["source_canary_present"])

    def test_postcard_preview_renders_establishment_and_local_landing_reference(self) -> None:
        try:
            _proof_browser()
        except RuntimeError as exc:
            if "Chromium is not installed" in str(exc):
                self.skipTest(f"Playwright Chromium is not installed: {exc}")
            raise

        with tempfile.TemporaryDirectory() as tmp:
            result = OSHA.render_outreach_proof(
                {
                    "establishment_id": "synthetic-1",
                    "establishment_name": "Example Manufacturing",
                    "industry_code": "332710",
                    "address": "1 Example Road",
                    "city": "Town",
                    "state": "IL",
                    "zip_code": "60000",
                },
                output_dir=tmp,
            )
            front = Path(result["postcard"]["front_html"]).read_text(encoding="utf-8")
            back = Path(result["postcard"]["back_html"]).read_text(encoding="utf-8")
            landing = Path(result["landing_pages"]) / "synthetic-1.html"
            self.assertTrue(landing.is_file())
        self.assertIn("Example Manufacturing", front)
        self.assertNotIn("{{establishment_name}}", front)
        self.assertIn("landing/synthetic-1.html", back)
        self.assertNotIn("{{landing_url}}", back)
        self.assertEqual(result["mail_status"], "render_only")


if __name__ == "__main__":
    unittest.main()
