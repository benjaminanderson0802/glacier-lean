"""Independent acceptance checks against CMS NPPES API v2.1 response objects."""
import hashlib
import json
import os
from pathlib import Path

import pytest


NPI = '1881018208'


def test_captured_registry_object_selects_location_and_primary_taxonomy(subject, fixture_json, client_factory):
    payload = fixture_json('provider.json')
    text = json.dumps(payload, ensure_ascii=False)
    rows = subject.source.collect({'npis': [NPI]}, client_factory([text]))
    assert len(rows) == 1
    row = rows[0]
    assert row['record_id'] == row['npi'] == NPI
    assert row['name'] == 'MAYO CLINIC' and row['enumeration_type'] == 'NPI-2'
    assert row['registry_status'] == 'A'
    assert row['source_updated_at'] == '2021-04-12' and row['enumeration_date'] == '2014-02-05'
    assert row['taxonomy_code'] == '261QM1300X'
    assert row['taxonomy_description'] == 'Clinic/Center, Multi-Specialty'
    assert row['address'] == '200 1ST ST SW' and row['city'] == 'ROCHESTER'
    assert row['state'] == 'MN' and row['postal_code'] == '559050001'
    assert row['source_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert row['source_url'].startswith('https://npiregistry.cms.hhs.gov/api/?')
    assert row['retrieved_at'] and 'not license' in row['message']
    assert not ({'telephone_number', 'authorized_official_first_name', 'identifiers'} & row.keys())


def test_no_match_is_explicit_and_free(subject, client_factory):
    rows = subject.source.collect({'npis': [NPI]}, client_factory([{'result_count': 0, 'results': []}]))
    assert rows[0]['outcome'] == 'no_match' and rows[0]['billable'] is False
    assert 'no match found in nppes as of' in rows[0]['message'].lower()


def test_invalid_npi_checksum_is_rejected_before_source_request(subject, client_factory):
    client = client_factory([])
    with pytest.raises(ValueError, match='check digits'):
        subject.source.collect({'npis': ['1881018209']}, client)
    with pytest.raises(ValueError):
        subject.source.collect({'npis': []}, client)
    assert client.calls == []


def test_duplicate_inputs_are_queried_once_and_batch_partial_failure_is_retained(subject, fixture_json, client_factory):
    client = client_factory([fixture_json('provider.json')])
    rows = subject.source.collect({'npis': [NPI, NPI]}, client)
    assert len(rows) == 1 and len(client.calls) == 1

    partial_client = client_factory([fixture_json('provider.json'), RuntimeError('CMS 503 outage')])
    rows = subject.source.collect({'npis': [NPI, '1992999981']}, partial_client)
    assert len(rows) == 2
    assert rows[0]['outcome'] == 'ok' and rows[0]['billable'] is True
    assert rows[1]['outcome'] == 'uncertain' and rows[1]['billable'] is False
    assert 'uncertain - please check' in rows[1]['message'].lower()


def test_api_error_count_mismatch_and_identity_mismatch_are_uncertain(subject, fixture_json, client_factory):
    responses = [
        {'Errors': ['rate limit'], 'result_count': 0, 'results': []},
        {'result_count': 1, 'results': []},
    ]
    uncertain_rows = []
    for response in responses:
        row = subject.source.collect({'npis': [NPI]}, client_factory([response]))[0]
        assert row['outcome'] == 'uncertain' and row['billable'] is False
        uncertain_rows.append(row)

    payload = fixture_json('provider.json')
    payload['results'][0]['number'] = '1881018216'
    row = subject.source.collect({'npis': [NPI]}, client_factory([payload]))[0]
    assert row['outcome'] == 'uncertain' and row['billable'] is False
    assert 'uncertain - please check' in uncertain_rows[0]['message'].lower()


def test_unicode_name_optional_location_and_taxonomy_stay_unknown(subject, fixture_json, client_factory):
    payload = fixture_json('provider.json')
    result = payload['results'][0]
    result['basic']['organization_name'] = 'Clínica 東京'
    result['addresses'] = [address for address in result['addresses']
                           if address['address_purpose'] == 'MAILING']
    result['taxonomies'] = [dict(taxonomy, primary=False) for taxonomy in result['taxonomies']]
    row = subject.source.collect({'npis': [NPI]}, client_factory([payload]))[0]
    assert row['name'] == 'Clínica 東京'
    assert row['address'] is None and row['city'] is None and row['state'] is None
    assert row['taxonomy_code'] is None and row['taxonomy_description'] is None
    assert any('practice address' in warning for warning in row['warnings'])
    assert any('primary taxonomy' in warning for warning in row['warnings'])


def test_malformed_source_fails_closed_and_uncertainty_uses_required_vocabulary(subject, client_factory):
    rows = subject.source.collect({'npis': [NPI]}, client_factory(['not-json']))
    assert rows[0]['outcome'] == 'uncertain' and rows[0]['billable'] is False
    assert 'uncertain - please check' in rows[0]['message'].lower()


def test_charge_only_after_success_row_is_written(deliver_rows):
    events = deliver_rows([
        {'record_id': NPI, 'outcome': 'ok', 'billable': True},
        {'record_id': 'outage', 'outcome': 'uncertain', 'billable': False},
    ])
    assert [event[0] for event in events] == ['push', 'charge', 'push', 'status']
    assert events[0][1]['record_id'] == NPI
    assert events[1][1]['event_name'] == 'provider-record'
    same_run = deliver_rows([{'record_id': NPI, 'outcome': 'ok', 'billable': True}])
    assert same_run[1][1]['idempotency_key'] == events[1][1]['idempotency_key']


def test_charge_limit_and_failed_dataset_write_never_overcharge(deliver_rows):
    row = {'record_id': NPI, 'outcome': 'ok', 'billable': True}
    assert [event[0] for event in deliver_rows([row], limit=True)] == ['status']
    assert [event[0] for event in deliver_rows([row, dict(row, record_id='1992999981')],
                                                charge_reaches_limit=True)] == ['push', 'charge', 'status']
    with pytest.raises(OSError, match='dataset write'):
        deliver_rows([row], fail_write=True)


def test_outage_only_and_no_match_rows_never_charge(subject, client_factory, deliver_rows):
    outage = subject.source.collect({'npis': [NPI]}, client_factory([RuntimeError('CMS 503 outage')]))
    no_match = subject.source.collect({'npis': [NPI]}, client_factory([{'result_count': 0, 'results': []}]))
    events = deliver_rows(outage + no_match)
    assert [event[0] for event in events] == ['push', 'push', 'status']


def test_public_http_retry_bounds_timeout_size_and_redirect_policy(subject, assert_http_policy):
    assert_http_policy(subject.runtime)


def test_prefill_executes_actor_main_and_writes_local_dataset(run_local):
    rows = run_local()
    row = next(row for row in rows if row.get('npi') == NPI)
    assert row['outcome'] == 'ok' and row['name'] == 'MAYO CLINIC'
    assert row['taxonomy_code'] == '261QM1300X'
    assert row['source_sha256']


@pytest.mark.skipif(os.getenv('RUN_LIVE') != '1', reason='set RUN_LIVE=1 for the single live source canary')
def test_live_prefill_canary_once(run_local, prefill):
    rows = run_local(live=True)
    assert prefill == {'npis': [NPI]}
    row = next(row for row in rows if row.get('npi') == NPI)
    assert row['outcome'] == 'ok' and row['name'] == 'MAYO CLINIC'
    assert row['source_url'].startswith('https://npiregistry.cms.hhs.gov/api/?')
    evidence = Path(__file__).parent / 'evidence' / 'acceptance-live.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({'input': prefill, 'rows': rows}, ensure_ascii=False, indent=2) + '\n')
