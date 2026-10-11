"""Independent acceptance checks based on the Census State ASCII contract."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path

import pytest


def _source_rows(subject, fixture_text, client_factory, **inputs):
    client = client_factory([fixture_text('august.txt'), fixture_text('july.txt')])
    return subject.source.collect({'period': '2026-08', **inputs}, client), client


def test_captured_official_rows_preserve_fips_units_and_provenance(subject, fixture_text, client_factory):
    rows, client = _source_rows(subject, fixture_text, client_factory, states=['01'])
    assert len(rows) == 1
    row = rows[0]
    assert row['state_fips'] == '01'
    assert row['name'] == 'Alabama'
    assert row['outcome'] == 'ok' and row['billable'] is True
    assert row['period'] == '2026-08' and row['previous_period'] == '2026-07'
    assert row['units'] == 1731 and row['reported_units'] == 1318
    assert row['valuation_usd'] == 451645000
    assert row['source_url'].endswith('/st2608c.txt')
    assert row['previous_source_url'].endswith('/st2607c.txt')
    assert row['source_sha256'] == hashlib.sha256(fixture_text('august.txt').encode()).hexdigest()
    assert row['previous_source_sha256'] == hashlib.sha256(fixture_text('july.txt').encode()).hexdigest()
    assert row['retrieved_at'] and row['source_last_modified']
    assert len(client.calls) == 2


def test_census_ascii_edge_cases_empty_malformed_duplicate_and_unicode(subject, fixture_text):
    source = fixture_text('august.txt')
    with pytest.raises(subject.source.SourceError):
        subject.source.parse('', '2026-08')
    with pytest.raises(subject.source.SourceError):
        subject.source.parse(source.replace('Survey,FIPS', 'Changed,FIPS', 1), '2026-08')
    first = next(line for line in source.splitlines() if line.startswith('202608,01,'))
    with pytest.raises(subject.source.SourceError, match='Duplicate'):
        subject.source.parse(source + first + '\n', '2026-08')
    unicode_source = source.replace('202608,01,3,6,Alabama,', '202608,01,3,6,Alabamá,', 1)
    assert subject.source.parse(unicode_source, '2026-08')['01']['name'] == 'Alabamá'


def test_missing_state_or_numeric_cell_is_uncertain_and_not_a_negative(subject, fixture_text, client_factory):
    current = fixture_text('august.txt')
    previous = fixture_text('july.txt')
    parsed = list(csv.reader(io.StringIO(current)))
    alabama = next(row for row in parsed if row[:2] == ['202608', '01'])
    alabama[6] = ''
    output = io.StringIO(newline='')
    csv.writer(output, lineterminator='\n').writerows(parsed)
    missing_value = output.getvalue()
    rows = subject.source.collect({'period': '2026-08', 'states': ['01']},
                                  client_factory([missing_value, previous]))
    assert rows[0]['outcome'] == 'uncertain' and rows[0]['billable'] is False
    assert rows[0]['state_fips'] == '01'
    absent = subject.source.collect({'period': '2026-08', 'states': ['99']},
                                    client_factory([current, previous]))
    assert absent[0]['outcome'] == 'uncertain' and absent[0]['billable'] is False


def test_source_outage_is_uncertain_and_says_uncertain_please_check(subject, client_factory):
    rows = subject.source.collect({'period': '2026-08', 'states': ['01']},
                                  client_factory([RuntimeError('503 source outage')]))
    assert rows and all(row['outcome'] == 'uncertain' and row['billable'] is False for row in rows)
    assert 'uncertain - please check' in rows[0]['message'].lower()


def test_charge_only_after_success_row_is_written(deliver_rows):
    events = deliver_rows([
        {'record_id': '01:2026-08:2026-07', 'outcome': 'ok', 'billable': True},
        {'record_id': '02', 'outcome': 'uncertain', 'billable': False},
    ])
    assert [event[0] for event in events] == ['push', 'charge', 'push', 'status']
    assert events[0][1]['record_id'] == '01:2026-08:2026-07'
    assert events[1][1]['event_name'] == 'state-comparison'
    assert events[1][1]['idempotency_key']
    same_run = deliver_rows([{'record_id': '01:2026-08:2026-07', 'outcome': 'ok', 'billable': True}])
    assert same_run[1][1]['idempotency_key'] == events[1][1]['idempotency_key']


def test_charge_limit_and_failed_dataset_write_never_overcharge(deliver_rows):
    row = {'record_id': '01:2026-08:2026-07', 'outcome': 'ok', 'billable': True}
    assert [event[0] for event in deliver_rows([row], limit=True)] == ['status']
    assert [event[0] for event in deliver_rows([row, dict(row, record_id='22')],
                                                charge_reaches_limit=True)] == ['push', 'charge', 'status']
    with pytest.raises(OSError, match='dataset write'):
        deliver_rows([row], fail_write=True)


def test_outage_only_and_no_match_rows_never_charge(subject, client_factory, fixture_text, deliver_rows):
    outage = subject.source.collect({'period': '2026-08', 'states': ['01']},
                                    client_factory([RuntimeError('503 source outage')]))
    no_match = subject.source.collect({'period': '2026-08', 'states': ['99']},
                                      client_factory([fixture_text('august.txt'), fixture_text('july.txt')]))
    events = deliver_rows(outage + no_match)
    assert [event[0] for event in events] == ['push', 'push', 'status']


def test_public_http_retry_bounds_timeout_size_and_redirect_policy(subject, assert_http_policy):
    assert_http_policy(subject.runtime)


def test_prefill_executes_actor_main_and_writes_local_dataset(run_local):
    rows = run_local()
    row = next(row for row in rows if row.get('state_fips') == '01')
    assert row['outcome'] == 'ok' and row['name'] == 'Alabama'
    assert row['period'] == '2026-08' and row['previous_period'] == '2026-07'
    assert row['source_sha256'] and row['previous_source_sha256']
    assert 'uncertain - please check' not in row['message'].lower()


@pytest.mark.skipif(os.getenv('RUN_LIVE') != '1', reason='set RUN_LIVE=1 for the single live source canary')
def test_live_prefill_canary_once(run_local, prefill):
    rows = run_local(live=True)
    assert prefill == {'period': 'latest', 'states': ['01', '22', '28']}
    assert {row['state_fips'] for row in rows if row['outcome'] == 'ok'} == {'01', '22', '28'}
    assert all(row['source_url'].startswith('https://www2.census.gov/econ/bps/State/st') for row in rows)
    evidence = Path(__file__).parent / 'evidence' / 'acceptance-live.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({'input': prefill, 'rows': rows}, ensure_ascii=False, indent=2) + '\n')
