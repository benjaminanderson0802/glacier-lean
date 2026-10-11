from datetime import date

from ventures.blocks.deadlines import add, due


def test_offset_rules_due_once_on_each_due_date(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    add("claim-1", "2026-01-01", "30d|120d", "Carrier response")
    assert due("2026-01-30") == []
    assert len(due("2026-01-31")) == 1
    assert due("2026-01-31") == []
    assert len(due("2026-05-01")) == 1
    assert due("2026-05-01") == []


def test_osha_window_fires_at_start_end_and_once(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    add("osha-1", "2026-01-01", "jan2-mar2", "OSHA filing window")
    assert due("2026-01-01") == []
    first = due("2026-01-02")
    assert len(first) == 1 and first[0]["milestone"] == "window_open"
    assert due("2026-01-02") == []
    end = due("2026-03-02")
    assert len(end) == 1 and end[0]["milestone"] == "window_close"


def test_osha_item_added_after_window_targets_next_calendar_year(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    add("osha-next-year", "2026-12-01", "jan2-mar2", "OSHA filing window")
    assert due("2026-01-02") == []
    assert due("2027-01-02")[0]["milestone"] == "window_open"
    assert due("2027-03-02")[0]["milestone"] == "window_close"


def test_calendar_date_window_fires_start_mid_and_end(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    add("parcel-1", "2026-06-01", "2026-06-10|2026-07-05", "Cook County appeal window")
    assert due("2026-06-09") == []
    assert due("2026-06-10")[0]["milestone"] == "window_open"
    assert due("2026-06-20")[0]["milestone"] == "due_soon"
    assert due("2026-06-20") == []
    assert due("2026-07-05")[0]["milestone"] == "window_close"


def test_60_90_reminders_and_glacier_steps(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    add("warranty-1", "2026-01-01", "60d|90d", "Warranty deadline")
    first = due("2026-03-02")
    assert len(first) == 1
    assert first[0]["milestone"] == "reminder"
    reminder, approval = first[0]["glacier_steps"]
    assert reminder["type"] == "note"
    assert reminder["config"]["path"].startswith("ventures/deadline-reminders/")
    assert "2026-03-02" in reminder["config"]["template"]
    assert approval["type"] == "approval"
    assert "Warranty deadline" in approval["config"]["prompt"]
    assert due("2026-03-02") == []
    assert len(due("2026-04-01")) == 1


def test_invalid_rules_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("GLACIER_HOME", str(tmp_path))
    try:
        add("bad", "2026-01-01", "soonish", "Bad rule")
    except ValueError as exc:
        assert "unsupported" in str(exc).lower()
    else:
        raise AssertionError("unsupported rule was accepted")
