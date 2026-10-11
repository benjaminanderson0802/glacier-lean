"""Acceptance checks for the synthetic Indiana utility-study CSV fixture."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.utility_audit import estimate_predominant_use_csv


class PredominantUseCsvAcceptanceTests(unittest.TestCase):
    def test_bill_and_study_csv_produce_estimate_and_unsigned_st200_application_data(self):
        fixture = Path(__file__).parent / "fixtures" / "indiana_predominant_use_bills.csv"

        result = estimate_predominant_use_csv(fixture, as_of="2026-10-10")

        self.assertEqual(result["result"], "predominant-use threshold met — DOR review required")
        self.assertEqual(result["study"]["period_count"], 12)
        self.assertEqual(result["study"]["exempt_use_percentage"], 64.0)
        self.assertEqual(result["estimate"]["estimated_annual_tax_exemption_after_approval"], 840.0)
        self.assertEqual(result["application_data"]["form"], "ST-200")
        self.assertEqual(result["application_data"]["fields"]["utility_type"], "electricity")
        self.assertEqual(result["application_data"]["fields"]["meter_id"], "SYNTHETIC-METER-01")
        self.assertFalse(result["application_data"]["signed"])
        self.assertFalse(result["application_data"]["submitted"])

    def test_nonconsecutive_bill_periods_are_not_used_to_claim_a_study_result(self):
        fixture = Path(__file__).parent / "fixtures" / "indiana_predominant_use_bills.csv"
        rows = fixture.read_text(encoding="utf-8").replace("2025-06,", "2025-07,")
        temporary = Path(__file__).parent / "fixtures" / "indiana_predominant_use_gap.csv"
        try:
            temporary.write_text(rows, encoding="utf-8")
            result = estimate_predominant_use_csv(temporary, as_of="2026-10-10")
        finally:
            temporary.unlink(missing_ok=True)

        self.assertEqual(result["result"], "uncertain — please check")
        self.assertIsNone(result["application_data"])

    def test_threshold_at_or_below_50_percent_does_not_create_st200_application_data(self):
        fixture = Path(__file__).parent / "fixtures" / "indiana_predominant_use_bills.csv"
        temporary = Path(__file__).parent / "fixtures" / "indiana_predominant_use_below_threshold.csv"
        try:
            temporary.write_text(fixture.read_text(encoding="utf-8").replace(",640,", ",500,"), encoding="utf-8")
            result = estimate_predominant_use_csv(temporary, as_of="2026-10-10")
        finally:
            temporary.unlink(missing_ok=True)

        self.assertEqual(result["study"]["exempt_use_percentage"], 50.0)
        self.assertEqual(result["result"], "predominant-use threshold not met — professional review required")
        self.assertIsNone(result["estimate"]["estimated_annual_tax_exemption_after_approval"])
        self.assertIsNone(result["application_data"])


if __name__ == "__main__":
    unittest.main()
