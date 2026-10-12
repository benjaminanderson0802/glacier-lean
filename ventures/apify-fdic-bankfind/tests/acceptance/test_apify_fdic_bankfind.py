"""Independent acceptance checks against FDIC's nested institution envelope."""
import hashlib
import json
import os
from pathlib import Path

import pytest


def _envelope(fixture_json):
    return fixture_json('institution.json')


def test_captured_institution_fields_and_source_vintage(subject, fixture_json, client_factory):
    payload = _envelope(fixture_json)
    text = json.dumps(payload, ensure_ascii=False)
    rows = subject.source.collect({'certificate': '3510'}, client_factory([text]))
    assert len(rows) == 1
    row = rows[0]
    assert row['certificate'] == '3510' and row['record_id'] == '3510'
    assert row['name'] == 'Bank of America, National Association'
    assert row['active'] is True and row['state'] == 'NC' and row['city'] == 'Charlotte'
    assert row['postal_code'] == '28202' and row['source_updated_at'] == '2026-06-29'
    assert row['source_vintage'] == payload['meta']['index']['name']
    assert row['source_total'] == 1 and row['truncated'] is False
    assert row['source_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert row['source_url'].startswith('https://api.fdic.gov/banks/institutions?')
    assert row['retrieved_at'] and 'not a bank safety' in row['message']


def test_explicit_empty_result_is_free_no_match(subject, fixture_json, client_factory):
    empty = _envelope(fixture_json)
    empty['meta']['total'] = 0
    empty['data'] = []
    empty['totals']['count'] = 0
    rows = subject.source.collect({'certificate': '999999'}, client_factory([empty]))
    assert len(rows) == 1 and rows[0]['outcome'] == 'no_match' and rows[0]['billable'] is False
    assert 'no match found in fdic as of' in rows[0]['message'].lower()


def test_partial_page_outage_and_vintage_change_discard_partial_rows(subject, fixture_json, client_factory):
    first = _envelope(fixture_json)
    first['meta']['total'] = 2
    first['meta']['parameters']['limit'] = '1'
    rows = subject.source.collect({'state': 'NC', 'page_size': 1},
                                  client_factory([first, RuntimeError('source timeout on page two')]))
    assert len(rows) == 1 and rows[0]['outcome'] == 'uncertain' and rows[0]['billable'] is False

    second = json.loads(json.dumps(first))
    first['data'][0]['data']['CERT'] = 3510
    second['meta']['index']['name'] = 'new-vintage'
    second['meta']['parameters']['offset'] = '1'
    second['data'] = [{'data': dict(first['data'][0]['data'], CERT=3511), 'score': 0}]
    second['meta']['total'] = 2
    rows = subject.source.collect({'state': 'NC', 'page_size': 1}, client_factory([first, second]))
    assert len(rows) == 1 and rows[0]['outcome'] == 'uncertain' and rows[0]['billable'] is False


def test_unicode_and_optional_fields_are_preserved_without_following_links(subject, fixture_json, client_factory):
    payload = _envelope(fixture_json)
    bank = payload['data'][0]['data']
    bank['NAME'] = 'Banque Démo 東京'
    bank['CITY'] = 'Québec'
    del bank['ZIP'], bank['DATEUPDT'], bank['WEBADDR']
    rows = subject.source.collect({'certificate': '3510'}, client_factory([payload]))
    row = rows[0]
    assert row['name'] == 'Banque Démo 東京' and row['city'] == 'Québec'
    assert row['postal_code'] is None and row['source_updated_at'] is None and row['website'] is None
    assert row['record_url'] == 'https://banks.data.fdic.gov/bankfind-suite/bankfind/details/3510'


def test_malformed_or_changed_source_is_uncertain_not_empty(subject, client_factory):
    rows = subject.source.collect({'certificate': '3510'}, client_factory(['{broken json']))
    assert rows[0]['outcome'] == 'uncertain' and rows[0]['billable'] is False
    rows = subject.source.collect({'certificate': '3510'}, client_factory([RuntimeError('HTTP 503')]))
    assert rows[0]['outcome'] == 'uncertain' and rows[0]['billable'] is False
    assert 'uncertain - please check' in rows[0]['message'].lower()


def test_page_limit_and_record_identity_are_validated(subject, fixture_json, client_factory):
    payload = _envelope(fixture_json)
    payload['data'][0]['data']['CERT'] = 3511
    rows = subject.source.collect({'certificate': '3510'}, client_factory([payload]))
    assert rows[0]['outcome'] == 'uncertain' and rows[0]['billable'] is False
    with pytest.raises(ValueError):
        subject.source.collect({'certificate': 3510}, client_factory([]))
    with pytest.raises(ValueError):
        subject.source.collect({'certificate': '3510', 'max_records': True}, client_factory([]))


def test_charge_only_after_success_row_is_written(deliver_rows):
    events = deliver_rows([
        {'record_id': '3510', 'outcome': 'ok', 'billable': True},
        {'record_id': 'uncertain', 'outcome': 'uncertain', 'billable': False},
    ])
    assert [event[0] for event in events] == ['push', 'charge', 'push', 'status']
    assert events[0][1]['record_id'] == '3510'
    assert events[1][1]['event_name'] == 'bank-record'
    same_run = deliver_rows([{'record_id': '3510', 'outcome': 'ok', 'billable': True}])
    assert same_run[1][1]['idempotency_key'] == events[1][1]['idempotency_key']


def test_charge_limit_and_failed_dataset_write_never_overcharge(deliver_rows):
    row = {'record_id': '3510', 'outcome': 'ok', 'billable': True}
    assert [event[0] for event in deliver_rows([row], limit=True)] == ['status']
    assert [event[0] for event in deliver_rows([row, dict(row, record_id='3511')],
                                                charge_reaches_limit=True)] == ['push', 'charge', 'status']
    with pytest.raises(OSError, match='dataset write'):
        deliver_rows([row], fail_write=True)


def test_outage_only_and_no_match_rows_never_charge(subject, fixture_json, client_factory, deliver_rows):
    outage = subject.source.collect({'certificate': '3510'}, client_factory([RuntimeError('503 outage')]))
    empty = _envelope(fixture_json)
    empty['meta']['total'] = 0
    empty['data'] = []
    empty['totals']['count'] = 0
    no_match = subject.source.collect({'certificate': '999999'}, client_factory([empty]))
    events = deliver_rows(outage + no_match)
    assert [event[0] for event in events] == ['push', 'push', 'status']


def test_public_http_retry_bounds_timeout_size_and_redirect_policy(subject, assert_http_policy):
    assert_http_policy(subject.runtime)


def test_prefill_executes_actor_main_and_writes_local_dataset(run_local):
    rows = run_local()
    row = next(row for row in rows if row.get('certificate') == '3510')
    assert row['outcome'] == 'ok' and row['name'] == 'Bank of America, National Association'
    assert row['source_vintage'] and row['source_sha256']
    assert row['postal_code'] == '28202'


@pytest.mark.skipif(os.getenv('RUN_LIVE') != '1', reason='set RUN_LIVE=1 for the single live source canary')
def test_live_prefill_canary_once(run_local, prefill):
    rows = run_local(live=True)
    assert prefill == {'certificate': '3510', 'active_only': False, 'max_records': 100}
    row = next(row for row in rows if row.get('certificate') == '3510')
    assert row['outcome'] == 'ok' and row['name'] == 'Bank of America, National Association'
    assert row['source_url'].startswith('https://api.fdic.gov/banks/institutions?')
    evidence = Path(__file__).parent / 'evidence' / 'acceptance-live.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({'input': prefill, 'rows': rows}, ensure_ascii=False, indent=2) + '\n')
