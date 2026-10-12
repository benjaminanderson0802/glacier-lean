"""Independent support, deliberately local to each standalone Actor's tests."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace
from urllib.parse import urlencode, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / 'fixtures'
HOSTS = {
    'apify-census-permits': 'www2.census.gov',
    'apify-fdic-bankfind': 'api.fdic.gov',
    'apify-npi-batch': 'npiregistry.cms.hhs.gov',
}


@pytest.fixture
def subject():
    # Separate package names prevent the three standalone `src` packages colliding.
    name = ROOT.name.replace('-', '_') + '_acceptance_subject'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / 'src/__init__.py',
            submodule_search_locations=[str(ROOT / 'src')])
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
    return SimpleNamespace(source=__import__(name + '.source', fromlist=['collect']),
        runtime=__import__(name + '.runtime', fromlist=['deliver']), root=ROOT)


@pytest.fixture(autouse=True)
def no_accidental_network(monkeypatch):
    import socket
    permission = threading.local()
    original_connect = socket.socket.connect
    original_pair = socket.socketpair

    def local_pair(*args, **kwargs):
        # Windows asyncio uses CPython's TCP socketpair fallback for its wakeup
        # pipe. Permit only that synchronous stdlib call, not arbitrary localhost.
        permission.socketpair = True
        try:
            return original_pair(*args, **kwargs)
        finally:
            permission.socketpair = False

    def guarded_connect(sock, address):
        if (getattr(permission, 'socketpair', False) and isinstance(address, tuple)
                and address[0] in ('127.0.0.1', '::1')):
            return original_connect(sock, address)
        raise AssertionError('Acceptance parent process must not open network sockets')

    def denied(*args, **kwargs):
        raise AssertionError('Acceptance parent process must not open network sockets')
    monkeypatch.setattr(socket, 'socketpair', local_pair)
    monkeypatch.setattr(socket.socket, 'connect', guarded_connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)


@pytest.fixture
def fixture_text():
    return lambda name: (FIXTURES / name).read_text(encoding='utf-8-sig')


@pytest.fixture
def fixture_json(fixture_text):
    return lambda name: json.loads(fixture_text(name))


@pytest.fixture
def client_factory():
    class ScriptedClient:
        def __init__(self, replies):
            self.replies = list(replies)
            self.calls = []
        def get(self, url, params=None):
            assert urlparse(url).hostname == HOSTS[ROOT.name]
            self.calls.append((url, params))
            assert self.replies, 'Unexpected additional source request'
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            text = reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
            return text, url + ('?' + urlencode(params) if params else ''), {'Last-Modified': 'Thu, 24 Sep 2026 11:46:16 GMT'}
    return ScriptedClient


@pytest.fixture
def assert_http_policy(monkeypatch):
    def check(runtime):
        class Response:
            def __init__(self, status, retry_after=None, body=b'{"ok":true}'):
                self.status_code = status
                self.headers = {'Retry-After': retry_after} if retry_after is not None else {}
                self.url = 'https://npiregistry.cms.hhs.gov/api/'
                self.body = body
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def iter_content(self, chunk_size): return [self.body]

        calls = []
        replies = [Response(429, '1'), Response(200)]
        def get(url, **kwargs):
            calls.append((url, kwargs))
            return replies.pop(0)
        monkeypatch.setattr(runtime.requests, 'get', get)
        monkeypatch.setattr(runtime.time, 'sleep', lambda seconds: None)
        text, _, _ = runtime.Client().get('https://npiregistry.cms.hhs.gov/api/')
        assert text == '{"ok":true}' and len(calls) == 2
        assert all(call[1]['allow_redirects'] is False for call in calls)
        assert all(call[1]['timeout'] == (10, 30) and call[1]['stream'] is True for call in calls)

        calls.clear()
        replies[:] = [Response(429, 'Wed, 21 Oct 2015 07:28:00 GMT')]
        with pytest.raises(runtime.SourceError):
            runtime.Client().get('https://npiregistry.cms.hhs.gov/api/')
        assert len(calls) == 1, 'HTTP-date Retry-After must not trigger a second request'

        calls.clear()
        replies[:] = [Response(200, body=b'x' * 5_000_001)]
        with pytest.raises(runtime.SourceError, match='5 MB'):
            runtime.Client().get('https://npiregistry.cms.hhs.gov/api/')
        assert len(calls) == 1
    return check


@pytest.fixture
def actor_double():
    class ActorDouble:
        def __init__(self, limit=False, charge_reaches_limit=False, fail_write=False):
            self.events = []
            self.limit = limit
            self.charge_reaches_limit = charge_reaches_limit
            self.fail_write = fail_write
        def get_charging_manager(self):
            return self
        def is_event_charge_limit_reached(self, event):
            return self.limit
        async def push_data(self, row):
            if self.fail_write:
                raise OSError('local dataset write failed')
            self.events.append(('push', row))
        async def charge(self, **kwargs):
            self.events.append(('charge', kwargs))
            return SimpleNamespace(event_charge_limit_reached=self.charge_reaches_limit)
        async def set_status_message(self, message, **kwargs):
            self.events.append(('status', message))
    return ActorDouble


@pytest.fixture
def deliver_rows(subject, actor_double, monkeypatch):
    def deliver(rows, *, cloud=True, **kwargs):
        monkeypatch.setenv('APIFY_IS_AT_HOME', '1' if cloud else '0')
        monkeypatch.setenv('APIFY_ACTOR_RUN_ID', 'independent-test-run')
        actor = actor_double(**kwargs)
        event = json.loads((ROOT / 'pricing.json').read_text())['event']
        asyncio.run(subject.runtime.deliver(actor, rows, event))
        return actor.events
    return deliver


@pytest.fixture
def prefill():
    schema = json.loads((ROOT / '.actor/input_schema.json').read_text())
    return {key: value.get('prefill', value.get('default'))
            for key, value in schema['properties'].items()
            if 'prefill' in value or 'default' in value}


@pytest.fixture
def run_local(tmp_path, prefill, record_property):
    def run(*, live=False):
        storage = tmp_path / ('live' if live else 'offline')
        kv = storage / 'key_value_stores/default'
        kv.mkdir(parents=True)
        (kv / 'INPUT.json').write_text(json.dumps(prefill))
        # Deliberate environment allowlist: never inherit a token, account or cloud store.
        env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'SYSTEMROOT') if key in os.environ}
        env.update(HOME=str(tmp_path), USERPROFILE=str(tmp_path),
            TEMP=str(tmp_path), TMP=str(tmp_path), PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
            GLACIER_HOME=str(tmp_path / 'glacier'), APIFY_IS_AT_HOME='0',
            APIFY_LOCAL_STORAGE_DIR=str(storage), CRAWLEE_STORAGE_DIR=str(storage),
            CRAWLEE_PURGE_ON_START='false', APIFY_DISABLE_OUTDATED_WARNING='1')
        command = [sys.executable, str(Path(__file__).parent / 'local_runner.py'),
                   str(ROOT), str(FIXTURES), str(storage), 'live' if live else 'offline']
        result = subprocess.run(command, cwd=ROOT, env=env, text=True, encoding='utf-8',
                                capture_output=True, timeout=180)
        record_property('local_main_input', json.dumps(prefill))
        record_property('local_main_exit', result.returncode)
        print(result.stdout, result.stderr)
        assert result.returncode == 0, result.stderr
        files = sorted((storage / 'datasets/default').glob('[0-9]*.json'))
        rows = [json.loads(path.read_text(encoding='utf-8')) for path in files]
        audit = json.loads((storage / 'acceptance-network.json').read_text())
        record_property('network_audit', json.dumps(audit))
        record_property('dataset', json.dumps(rows, ensure_ascii=False))
        assert audit and all(item['method'] == 'GET' and item['host'] == HOSTS[ROOT.name] for item in audit)
        assert rows, 'Successful exit alone is not evidence of a delivered result'
        return rows
    return run
