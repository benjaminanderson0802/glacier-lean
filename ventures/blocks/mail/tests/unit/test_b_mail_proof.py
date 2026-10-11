from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import patch

from ventures.blocks.mail import postcard


SENDER = {
    "name": "Fixture Sender Co.",
    "address_line1": "12 Proof Lane",
    "address_line2": "Suite 4",
    "address_city": "Fixtureville",
    "address_state": "WI",
    "address_zip": "53703",
}


def test_long_copy_blocks_instead_of_returning_a_partial_proof(tmp_path: Path) -> None:
    front = "<main><p>FRONT-START</p><p>" + " ".join(f"front-copy-{index:03d}" for index in range(320)) + "</p><p>FRONT-END</p><p>Fixture Sender Co.</p></main>"
    back = "<main><p>BACK-START</p><p>" + " ".join(f"back-copy-{index:03d}" for index in range(320)) + "</p><p>BACK-END</p><p>Fixture Sender Co.</p></main>"

    with patch.dict(os.environ, {"LOB_API_KEY": ""}):
        result = postcard(front, back, {"address": "1 Test Street"}, SENDER, output_dir=tmp_path)

    assert result["status"] == "blocked_overflow"
    assert "overflow" in result["blocking_reason"]
    assert result["proof_pdf"] is None


def test_styled_review_pdf_keeps_copy_sender_and_standard_dimensions(tmp_path: Path) -> None:
    front = (
        "<main><h1>FRONT-HEADLINE</h1><p>Fixture Sender Co. offers <em>emphasized service</em>.</p>"
        "<ul><li>FRONT-LIST-ITEM</li></ul><p><a href=\"https://example.invalid\">FRONT-LINK-TEXT</a></p></main>"
    )
    back = (
        "<main><h2>BACK-HEADING</h2><p>Reviewed back copy with <strong>important wording</strong>.</p>"
        "<ul><li>BACK-LIST-ITEM</li></ul><p><a href=\"https://example.invalid\">BACK-LINK-TEXT</a></p>"
        "<p>Fixture Sender Co.</p></main>"
    )

    with patch.dict(os.environ, {"LOB_API_KEY": ""}):
        result = postcard(front, back, {"address": "1 Test Street"}, SENDER, output_dir=tmp_path)

    assert result["status"] == "render_only"
    assert result["proof_kind"] == "local_review"
    assert result["proof_dimensions_inches"] == {"width": 6, "height": 4}
    assert result["proof_notice"] == "Local review proof only; not print-ready."
    proof = Path(result["proof_pdf"])
    assert proof.is_file()
    assert proof.read_bytes().startswith(b"%PDF-")
    assert len(re.findall(rb"/Type /Page\b", proof.read_bytes())) == 2
    assert proof.read_bytes().count(b"/MediaBox [0 0 432 288]") == 2
    saved_front = Path(result["front_html"]).read_text(encoding="utf-8")
    saved_back = Path(result["back_html"]).read_text(encoding="utf-8")
    for marker in (
        "FRONT-HEADLINE", "emphasized service", "FRONT-LIST-ITEM", "FRONT-LINK-TEXT", "Fixture Sender Co.",
    ):
        assert marker in saved_front
    for marker in ("BACK-HEADING", "important wording", "BACK-LIST-ITEM", "BACK-LINK-TEXT", "Fixture Sender Co."):
        assert marker in saved_back


def test_eddm_page_rule_is_not_mislabeled_as_the_standard_preview(tmp_path: Path) -> None:
    front = "<style>@page { size: 11.5in 6.25in; margin: 0 }</style><p>Fixture Sender Co.</p>"
    with patch.dict(os.environ, {"LOB_API_KEY": ""}):
        result = postcard(front, "<p>Short back copy</p>", {"address": "1 Test Street"}, SENDER, output_dir=tmp_path)

    if result["status"] == "blocked_overflow":
        assert result["proof_pdf"] is None
        assert "overflow" in result["blocking_reason"]
    else:
        assert result["status"] == "render_only"
        proof = Path(result["proof_pdf"])
        assert len(re.findall(rb"/Type /Page\b", proof.read_bytes())) == 2
        assert proof.read_bytes().count(b"/MediaBox [0 0 432 288]") == 2
