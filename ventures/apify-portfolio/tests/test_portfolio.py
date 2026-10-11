"""Builder regression tests; existing independent acceptance checks remain untouched."""
import asyncio
import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name, part='source'):
    package = 'portfolio_' + name.replace('-', '_')
    root = ROOT / ('apify-' + name) / 'src'
    if package not in sys.modules:
        spec = importlib.util.spec_from_file_location(package, root / '__init__.py', submodule_search_locations=[str(root)])
        obj = importlib.util.module_from_spec(spec)
        sys.modules[package] = obj
        spec.loader.exec_module(obj)
    return __import__(package + '.' + part, fromlist=[part])


def fixture(name):
    return (ROOT / 'apify-portfolio' / 'evidence' / name).read_text()


class Client:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
    def get(self, url, params=None):
        self.calls.append((url, params))
        data = self.responses.pop(0)
        if isinstance(data, Exception):
            raise data
        return data, url, {'Last-Modified': 'Thu, 24 Sep 2026 11:46:00 GMT'}


def test_fdic_real_shape_and_provenance():
    rows = module('fdic-bankfind').collect({'certificate': '3510'}, Client(fixture('fdic-source.txt')))
    assert len(rows) == 1
    assert rows[0]['certificate'] == '3510'
    assert rows[0]['name'] == 'Bank of America, National Association'
    assert rows[0]['active'] is True
    assert rows[0]['source_updated_at'] == '2026-06-29'
    assert rows[0]['source_vintage'] == 'institutions_20261009090008'


def test_fdic_pagination_cap_and_deduplication():
    base = json.loads(fixture('fdic-source.txt'))
    base['meta']['total'] = 3
    second = copy.deepcopy(base)
    second['data'][0]['data']['CERT'] = 999
    c = Client(json.dumps(base), json.dumps(second))
    rows = module('fdic-bankfind').collect({'state': 'NC', 'max_records': 2, 'page_size': 1}, c)
    assert [r['certificate'] for r in rows] == ['3510', '999']
    assert all(r['truncated'] for r in rows)
    assert [call[1]['offset'] for call in c.calls] == [0, 1]
    c = Client(json.dumps(base), json.dumps(base))
    rows = module('fdic-bankfind').collect({'state': 'NC', 'max_records': 2, 'page_size': 1}, c)
    assert rows[-1]['outcome'] == 'uncertain'
    assert all(not r['billable'] for r in rows)


def test_census_real_two_header_csv_and_delta():
    c = Client(fixture('st2608c.txt'), fixture('st2607c.txt'))
    row = module('census-permits').collect({'period': '2026-08', 'previous_period': '2026-07', 'states': ['01']}, c)[0]
    assert row['units'] == 1731
    assert row['previous_units'] == 1560
    assert row['units_change'] == 171
    assert row['valuation_usd'] == 451645000
    assert row['reported_units'] == 1318
    assert row['outcome'] == 'ok' and row['billable']
    assert row['period'] == '2026-08'


def test_census_missing_state_is_uncertain_not_zero():
    c = Client(fixture('st2608c.txt'), fixture('st2607c.txt'))
    rows = module('census-permits').collect({'period': '2026-08', 'previous_period': '2026-07', 'states': ['72']}, c)
    assert rows[0]['outcome'] == 'uncertain'
    assert not rows[0]['billable']


def test_npi_real_shape_deduplicates_and_only_practice_address():
    c = Client(fixture('npi-example.json'))
    row = module('npi-batch').collect({'npis': ['1881018208', '1881018208']}, c)[0]
    assert len(c.calls) == 1
    assert row['npi'] == '1881018208'
    assert row['name'] == 'MAYO CLINIC'
    assert row['taxonomy_code'] == '261QM1300X'
    assert row['city'] == 'ROCHESTER'
    assert row['source_updated_at'] == '2021-04-12'
    assert row['outcome'] == 'ok'


def test_npi_empty_and_api_error_differ():
    source = module('npi-batch')
    empty = source.collect({'npis': ['1881018208']}, Client('{"result_count":0,"results":[]}'))[0]
    error = source.collect({'npis': ['1881018208']}, Client('{"Errors":[{"description":"Invalid request"}]}'))[0]
    assert empty['outcome'] == 'no_match' and not empty['billable']
    assert error['outcome'] == 'uncertain' and not error['billable']


@pytest.mark.parametrize('name,inputs', [('fdic-bankfind', {'certificate': '3510'}), ('census-permits', {'period': '2026-08', 'states': ['01']}), ('npi-batch', {'npis': ['1881018208']})])
@pytest.mark.parametrize('response', ['<html>outage</html>', '{}', RuntimeError('timeout')])
def test_outages_never_bill(name, inputs, response):
    rows = module(name).collect(inputs, Client(response))
    assert rows and all(r['outcome'] == 'uncertain' and not r['billable'] for r in rows)


@pytest.mark.parametrize('name,inputs', [('fdic-bankfind', {'state': 'NC OR *'}), ('census-permits', {'period': '../../secret'}), ('npi-batch', {'npis': ['123']})])
def test_invalid_input_precedes_network(name, inputs):
    c = Client()
    with pytest.raises(ValueError):
        module(name).collect(inputs, c)
    assert not c.calls


@pytest.mark.parametrize('name', ['fdic-bankfind', 'census-permits', 'npi-batch'])
def test_billing_only_success_and_stops_at_cap(name, monkeypatch):
    runner = module(name, 'runtime')
    monkeypatch.setenv('APIFY_IS_AT_HOME', '1')
    class Actor:
        def __init__(self): self.pushed, self.charges = [], []
        async def push_data(self, row): self.pushed.append(row)
        async def charge(self, **kw):
            self.charges.append(kw)
            return SimpleNamespace(event_charge_limit_reached=True)
        def get_charging_manager(self):
            return SimpleNamespace(is_event_charge_limit_reached=lambda event: False)
        async def set_status_message(self, *a, **kw): pass
    actor = Actor()
    rows = [{'outcome': 'uncertain', 'billable': False}, {'outcome': 'ok', 'billable': True, 'record_id': 'a'}, {'outcome': 'ok', 'billable': True, 'record_id': 'b'}]
    asyncio.run(runner.deliver(actor, rows, 'record'))
    assert len(actor.charges) == 1 and len(actor.pushed) == 2
    assert actor.charges[0]['idempotency_key']


def test_self_contained_packaging_and_shared_code():
    common = []
    for name in ['fdic-bankfind', 'census-permits', 'npi-batch']:
        root = ROOT / ('apify-' + name)
        assert (root / 'requirements.txt').read_bytes() == (ROOT / 'apify-tools/requirements.txt').read_bytes()
        actor = json.loads((root / '.actor/actor.json').read_text())
        schema = json.loads((root / '.actor/dataset_schema.json').read_text())
        assert actor['storages']['dataset'] == './dataset_schema.json'
        assert schema['views'] and schema['fields']['type'] == 'object'
        common.append((root / 'src/runtime.py').read_bytes())
    assert common[0] == common[1] == common[2]


def test_fdic_second_page_outage_discards_partial_paid_snapshot():
    base = json.loads(fixture('fdic-source.txt'))
    base['meta']['total'] = 2
    rows = module('fdic-bankfind').collect({'state': 'NC', 'page_size': 1}, Client(json.dumps(base), RuntimeError('503')))
    assert len(rows) == 1 and rows[0]['outcome'] == 'uncertain' and not rows[0]['billable']


def test_fdic_valid_empty_snapshot_is_free():
    payload = json.loads(fixture('fdic-source.txt'))
    payload['meta']['total'], payload['data'] = 0, []
    row = module('fdic-bankfind').collect({'certificate': '3510'}, Client(json.dumps(payload)))[0]
    assert row['outcome'] == 'no_match' and not row['billable']


def test_census_latest_discovery_and_previous_outage():
    c = Client('<a href="st2607c.txt"></a><a href="st2608c.txt"></a>', fixture('st2608c.txt'), fixture('st2607c.txt'))
    rows = module('census-permits').collect({'states': ['01']}, c)
    assert rows[0]['period'] == '2026-08'
    assert c.calls[1][0].endswith('/st2608c.txt')
    rows = module('census-permits').collect({'period': '2026-08'}, Client(fixture('st2608c.txt'), RuntimeError('503')))
    assert rows[0]['outcome'] == 'uncertain' and not rows[0]['billable']


def test_census_suppression_does_not_become_zero():
    text = fixture('st2608c.txt').replace('1317,1317,393913', '1317,N,393913', 1)
    row = module('census-permits').collect({'period': '2026-08', 'states': ['01']}, Client(text, fixture('st2607c.txt')))[0]
    assert row['outcome'] == 'uncertain' and 'units' not in row


def test_npi_identity_mismatch_is_free_uncertain():
    payload = json.loads(fixture('npi-example.json'))
    payload['results'][0]['number'] = '1234567893'
    row = module('npi-batch').collect({'npis': ['1881018208']}, Client(json.dumps(payload)))[0]
    assert row['outcome'] == 'uncertain' and not row['billable']


def test_client_rate_limit_timeout_redirect_and_retry_policy(monkeypatch):
    runtime = module('fdic-bankfind', 'runtime')
    calls, sleeps = [], []
    class Response:
        def __init__(self, status):
            self.status_code = status
            self.headers = {'Retry-After': '3'}
            self.url = 'https://api.fdic.gov/banks/institutions'
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, size): yield b'{}'
    responses = [Response(429), Response(200), Response(302)]
    def get(url, **kwargs):
        calls.append(kwargs)
        return responses.pop(0)
    monkeypatch.setattr(runtime.requests, 'get', get)
    monkeypatch.setattr(runtime.time, 'sleep', sleeps.append)
    client = runtime.Client()
    assert client.get('https://api.fdic.gov/banks/institutions')[0] == '{}'
    with pytest.raises(runtime.SourceError):
        client.get('https://api.fdic.gov/banks/institutions')
    assert 3 in sleeps and any(0 < x <= 1 for x in sleeps)
    assert all(c['allow_redirects'] is False and c['timeout'] == (10, 30) for c in calls)


def test_real_local_outputs_validate_dataset_schema():
    import jsonschema
    for name in ['fdic-bankfind', 'census-permits', 'npi-batch']:
        root = ROOT / ('apify-' + name)
        schema = json.loads((root / '.actor/dataset_schema.json').read_text())['fields']
        for row in json.loads((root / 'evidence/local-output.json').read_text())['rows']:
            jsonschema.validate(row, schema)


def test_census_late_column_reorder_fails_closed():
    text = fixture('st2608c.txt').replace('3-4 units', 'unexpected metric', 1)
    row = module('census-permits').collect({'period': '2026-08', 'states': ['01']}, Client(text, fixture('st2607c.txt')))[0]
    assert row['outcome'] == 'uncertain' and not row['billable']


def test_fdic_contradictory_total_fails_closed():
    payload = json.loads(fixture('fdic-source.txt'))
    payload['meta']['total'] = 0
    row = module('fdic-bankfind').collect({'certificate': '3510'}, Client(json.dumps(payload)))[0]
    assert row['outcome'] == 'uncertain' and not row['billable']
