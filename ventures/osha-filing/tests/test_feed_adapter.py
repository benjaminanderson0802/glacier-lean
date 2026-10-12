from __future__ import annotations

import ventures.blocks.feeds.core as core


def test_osha_adapter_finds_current_summary_and_returns_count(monkeypatch):
    config = {"url": "https://www.osha.gov/itadata"}
    responses = [
        b'<a href="/sites/default/largefiles/ITA_data_2025.csv">2025 Summary Data</a>',
        b'establishment_id,establishment_name,city,state,industry_description,size,year_filing_for\n123,Example,Chicago,IL,HVAC,3,2025\n'
    ]
    requested = []
    def fake_request(url, **kwargs):
        requested.append((url, kwargs))
        return responses.pop(0)
    monkeypatch.setattr(core, "_request", fake_request)
    rows, total, url = core._osha(config)
    assert total == len(rows) == 1
    assert rows[0]["establishment_id"] == "123"
    assert url == "https://www.osha.gov/sites/default/largefiles/ITA_data_2025.csv"
    assert requested[0][1]["max_bytes"] == 5_000_000
    assert requested[1][1]["max_bytes"] == 150_000_000


def test_osha_adapter_rejects_summary_without_establishment_id_canary(monkeypatch):
    responses = [
        b'<a href="/sites/default/largefiles/ITA_data_2025.csv">2025 Summary Data</a>',
        b'establishment_name,city,state\nExample,Chicago,IL\n'
    ]
    monkeypatch.setattr(core, "_request", lambda *_args, **_kwargs: responses.pop(0))
    try:
        core._osha({"url": "https://www.osha.gov/itadata"})
    except ValueError as exc:
        assert "establishment_ID" in str(exc) or "establishment_id" in str(exc)
    else:
        raise AssertionError("summary without the establishment-ID canary was accepted")


def test_osha_adapter_rejects_non_osha_download_target(monkeypatch):
    responses = [b'<a href="https://example.com/data.csv">2025 Summary Data</a>']
    monkeypatch.setattr(core, "_request", lambda *_args, **_kwargs: responses.pop(0))
    try:
        core._osha({"url": "https://www.osha.gov/itadata"})
    except ValueError as exc:
        assert "official OSHA" in str(exc)
    else:
        raise AssertionError("non-OSHA download target was accepted")


def test_request_stops_after_configured_byte_limit(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def read(self, size=-1): return b"x" * size
    monkeypatch.setattr(core.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    try:
        core._request("https://example.test", max_bytes=3)
    except ValueError as exc:
        assert "safety limit" in str(exc)
    else:
        raise AssertionError("oversized response was accepted")
