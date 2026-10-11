"""Independent black-box checks for owner-saved feed snapshot imports.

All input files are synthetic and local. These tests exercise the public importer
and inspect the disposable SQLite cache as a separate observer would.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date

import pytest

from ventures.blocks.feeds import core, query
from ventures.blocks.feeds.import_snapshot import import_snapshot


SOURCE_ID = "fsis_recalls"
SOURCE_URL = "https://www.fsis.usda.gov/news-events/news-feeds-subscriptions"


def _write_snapshot(path, records, *, total=None):
    payload = {"results": records}
    if total is not None:
        payload["total"] = total
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw)
    return raw


def _import(path, *, source_url=SOURCE_URL, acquired_at=None, **kwargs):
    return import_snapshot(
        SOURCE_ID,
        path,
        source_url=source_url,
        acquired_at=acquired_at or date.today().isoformat(),
        complete=True,
        **kwargs,
    )


def _state(tmp_path):
    database = tmp_path / "glacier" / "ventures" / "feeds.db"
    rows = query(SOURCE_ID)
    with sqlite3.connect(database) as con:
        schema = con.execute(
            "SELECT fields FROM feed_schemas WHERE source_id=?", (SOURCE_ID,)
        ).fetchone()
        provenance = con.execute(
            "SELECT source_url, acquired_at, sha256, format, row_count, complete, imported_at "
            "FROM feed_imports WHERE source_id=?",
            (SOURCE_ID,),
        ).fetchone()
    return rows, schema[0] if schema else None, provenance


def _trusted_file(tmp_path):
    path = tmp_path / "trusted.json"
    raw = _write_snapshot(
        path,
        [
            {
                "field_recall_number": "SYNTHETIC-TRUSTED-1",
                "field_recall_date": "2024-02-03",
                "field_title": "Synthetic baseline recall",
                "field_summary": "Fixture only",
            }
        ],
        total=1,
    )
    acquired_at = date.today().isoformat()
    result = _import(path, acquired_at=acquired_at)
    assert result["status"] == "ok"
    return path, raw, acquired_at


def test_imported_snapshot_preserves_exact_bytes_vintage_retrieval_and_provenance(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    monkeypatch.setattr(core, "_request", lambda *_args, **_kwargs: pytest.fail("import attempted network access"))

    path, raw, acquired_at = _trusted_file(tmp_path)
    first_rows, first_schema, first_provenance = _state(tmp_path)

    assert len(first_rows) == 1
    assert first_rows[0]["record_id"] == "SYNTHETIC-TRUSTED-1"
    assert first_rows[0]["record_date"] == "2024-02-03"  # source vintage
    assert first_rows[0]["fetched_at"] == f"{acquired_at}T00:00:00Z"  # retrieval date
    assert first_rows[0]["source_url"] == SOURCE_URL
    assert first_provenance[:6] == (
        SOURCE_URL,
        acquired_at,
        hashlib.sha256(raw).hexdigest(),
        "json",
        1,
        1,
    )
    assert first_provenance[6].endswith("Z")
    assert first_schema is not None

    repeated = _import(path, acquired_at=acquired_at)
    second_rows, second_schema, second_provenance = _state(tmp_path)
    assert repeated["status"] == "ok"
    assert repeated["changed"] is False
    assert repeated["idempotent"] is True
    assert second_rows == first_rows
    assert second_schema == first_schema
    assert second_provenance == first_provenance


@pytest.mark.parametrize("candidate_kind", ["malformed", "count_mismatch"])
def test_malformed_or_count_mismatched_candidate_cannot_replace_trusted_snapshot(
    tmp_path, monkeypatch, candidate_kind
):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    trusted, _, acquired_at = _trusted_file(tmp_path)
    before_rows, before_schema, before_provenance = _state(tmp_path)

    candidate = tmp_path / f"{candidate_kind}.json"
    if candidate_kind == "malformed":
        candidate.write_text('{"results":[', encoding="utf-8")
        result = _import(candidate, acquired_at=acquired_at)
    else:
        _write_snapshot(
            candidate,
            [
                {
                    "field_recall_number": "SYNTHETIC-MISMATCH-1",
                    "field_recall_date": "2024-02-04",
                    "field_title": "Synthetic mismatched count",
                    "field_summary": "Fixture only",
                }
            ],
        )
        result = _import(candidate, acquired_at=acquired_at, expected_row_count=3)

    after_rows, after_schema, after_provenance = _state(tmp_path)
    assert result["status"] == "failed"
    assert result["changed"] is False
    assert result["snapshot_available"] is True
    assert after_rows == before_rows
    assert after_schema == before_schema
    assert after_provenance == before_provenance
    assert trusted.is_file()


def test_wrong_registered_source_url_cannot_replace_trusted_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    _trusted_file(tmp_path)
    before_rows, before_schema, before_provenance = _state(tmp_path)
    candidate = tmp_path / "wrong-source.json"
    _write_snapshot(
        candidate,
        [
            {
                "field_recall_number": "SYNTHETIC-WRONG-SOURCE-1",
                "field_recall_date": "2024-02-05",
                "field_title": "Synthetic wrong source",
                "field_summary": "Fixture only",
            }
        ],
        total=1,
    )

    with pytest.raises(ValueError, match="registered official source host"):
        _import(candidate, source_url="https://example.invalid/fake-feed")

    after_rows, after_schema, after_provenance = _state(tmp_path)
    assert after_rows == before_rows
    assert after_schema == before_schema
    assert after_provenance == before_provenance


def test_duplicate_identifiers_never_promote_or_overwrite_trusted_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path / "glacier"))
    _trusted_file(tmp_path)
    before_rows, before_schema, before_provenance = _state(tmp_path)
    candidate = tmp_path / "duplicate-identifiers.json"
    duplicate = {
        "field_recall_number": "SYNTHETIC-DUPLICATE-1",
        "field_recall_date": "2024-02-06",
        "field_title": "Synthetic duplicate identifier",
        "field_summary": "Fixture only",
    }
    _write_snapshot(candidate, [duplicate, dict(duplicate)], total=2)

    result = _import(candidate)

    after_rows, after_schema, after_provenance = _state(tmp_path)
    assert after_rows == before_rows
    assert after_schema == before_schema
    assert after_provenance == before_provenance
    assert result["status"] == "failed"
    assert result["changed"] is False
