from ventures.blocks.reader import read_document


def test_csv_fields_include_page_confidence_and_uncertainty(tmp_path):
    path = tmp_path / "certificate.csv"
    path.write_text("product_id,manufacturer\nABC-7,Example Works\n", encoding="utf-8")

    result = read_document(path)

    assert result["text"]
    assert result["fields"]["product_id"] == {
        "value": "ABC-7", "page": 1, "confidence": 1.0, "uncertain": False
    }
    assert result["fields"]["manufacturer"]["value"] == "Example Works"


def test_schema_extraction_disagreement_is_uncertain(tmp_path, monkeypatch):
    from ventures.blocks import reader

    path = tmp_path / "certificate.txt"
    path.write_text("Product ID: ABC-7\n", encoding="utf-8")
    monkeypatch.setattr(reader, "_available_engines", lambda: [
        ("labels", lambda *_: {"product_id": {"value": "ABC-7", "page": 1, "confidence": 0.9}}),
        ("second", lambda *_: {"product_id": {"value": "XYZ-9", "page": 1, "confidence": 0.9}}),
    ])

    result = read_document(path, schema={"product_id": "Product ID"})

    assert result["fields"]["product_id"]["uncertain"] is True
    assert result["fields"]["product_id"]["value"] is None


def test_missing_second_engine_marks_schema_fields_uncertain(tmp_path, monkeypatch):
    from ventures.blocks import reader

    path = tmp_path / "certificate.txt"
    path.write_text("Product ID: ABC-7\n", encoding="utf-8")
    monkeypatch.setattr(reader, "_available_engines", lambda: [
        ("labels", lambda *_: {"product_id": {"value": "ABC-7", "page": 1, "confidence": 0.9}}),
    ])

    result = read_document(path, schema={"product_id": "Product ID"})

    assert result["fields"]["product_id"]["uncertain"] is True

