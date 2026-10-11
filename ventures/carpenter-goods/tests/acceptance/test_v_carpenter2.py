"""Independent maker listing and commission acceptance checks."""
import json
import sys
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "carpenter-goods"))

def load_listing_prep():
    spec = importlib.util.spec_from_file_location("acceptance_carpenter_listing_prep", ROOT / "carpenter-goods/scripts/listing_prep.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.xfail(strict=False, reason="awaiting builder V-CARPENTER2")
def test_agreement_template_has_plain_language_summary_and_legal_note():
    root = Path(__file__).resolve().parents[2]
    agreement = root / "agreement"
    docs = list(agreement.glob("*")) if agreement.exists() else []
    text = "\n".join(p.read_text(errors="ignore") for p in docs if p.is_file()).lower()
    assert "not legal advice" in text
    assert "summary" in text and ("____" in text or "[blank" in text or "[insert" in text)


@pytest.mark.xfail(strict=False, reason="awaiting builder V-CARPENTER2")
def test_product_sheet_csv_generates_etsy_shopify_drafts_without_publishing(tmp_path):
    root = Path(__file__).resolve().parents[2]
    templates = list(root.glob("**/*product*template*.csv"))
    assert templates, "product sheet CSV template is required"
    readme = (root / "README.md").read_text().lower()
    assert "etsy" in readme and "shopify" in readme and "draft" in readme
    assert "publish" in readme and "owner" in readme


def test_commission_calculator_uses_paid_sales_and_explicit_rate():
    calculate_commissions = load_listing_prep().calculate_commissions
    sales = [{"order_id": "A-1", "amount": "100.00", "status": "paid"}, {"order_id": "A-2", "amount": "50.00", "status": "unpaid"}]
    result = calculate_commissions(sales, 0.2)
    assert result["commission_due"] == 20.0
    assert result["eligible_sales"] == 1
