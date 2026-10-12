"""Execute the real Actor entrypoint with guarded local SDK storage.

Only the public source HTTP transport is replaced for offline tests. Live mode
uses that exact entrypoint and transport with GET/host guards, never Apify cloud.
"""
import json
from pathlib import Path
import runpy
import socket
import sys
import threading
from urllib.parse import urlparse, urlencode

import requests
from apify import Actor

root, fixtures, storage = map(Path, sys.argv[1:4])
live = sys.argv[4] == 'live'
sys.path.insert(0, str(root))
host = {'apify-census-permits': 'www2.census.gov', 'apify-fdic-bankfind': 'api.fdic.gov',
        'apify-npi-batch': 'npiregistry.cms.hhs.gov'}[root.name]
audit = []
permission = threading.local()
original_pair = socket.socketpair
original_connect = socket.socket.connect
original_request = requests.sessions.Session.request


def local_pair(*args, **kwargs):
    # asyncio's Windows wakeup pipe is a local TCP socketpair, not source IO.
    permission.socketpair = True
    try:
        return original_pair(*args, **kwargs)
    finally:
        permission.socketpair = False


def connect(sock, address):
    if (getattr(permission, 'socketpair', False) and isinstance(address, tuple)
            and address[0] in ('127.0.0.1', '::1')):
        return original_connect(sock, address)
    if not getattr(permission, 'source_request', False):
        raise AssertionError('External connection outside the approved source GET')
    return original_connect(sock, address)


def request(session, method, url, **kwargs):
    parsed = urlparse(url)
    assert method.upper() == 'GET' and parsed.scheme == 'https' and parsed.hostname == host
    assert not kwargs.get('allow_redirects', True), 'Redirects may escape the source boundary'
    audit.append({'method': method.upper(), 'host': parsed.hostname, 'url': url,
                  'params': kwargs.get('params')})
    if live:
        permission.source_request = True
        try:
            return original_request(session, method, url, **kwargs)
        finally:
            permission.source_request = False
    if root.name == 'apify-census-permits':
        bodies = {'/econ/bps/State/': b'<a href="st2608c.txt">August</a><a href="st2607c.txt">July</a>',
                  '/econ/bps/State/st2608c.txt': (fixtures / 'august.txt').read_bytes(),
                  '/econ/bps/State/st2607c.txt': (fixtures / 'july.txt').read_bytes()}
        body = bodies[parsed.path]
    else:
        body = (fixtures / ('institution.json' if root.name == 'apify-fdic-bankfind' else 'provider.json')).read_bytes()
    response = requests.Response()
    response.status_code = 200
    response._content = body
    response._content_consumed = True
    response.url = url + ('?' + urlencode(kwargs['params']) if kwargs.get('params') else '')
    response.headers['Last-Modified'] = 'Thu, 24 Sep 2026 11:46:16 GMT'
    return response


async def forbidden_charge(*args, **kwargs):
    raise AssertionError('Owner-only payment attempted during a local acceptance run')


socket.socketpair = local_pair
socket.socket.connect = connect
socket.socket.connect_ex = lambda *args: (_ for _ in ()).throw(AssertionError('Unexpected socket connect_ex'))
requests.sessions.Session.request = request
Actor.charge = forbidden_charge
try:
    runpy.run_module('src', run_name='__main__')
finally:
    (storage / 'acceptance-network.json').write_text(json.dumps(audit, indent=2))
