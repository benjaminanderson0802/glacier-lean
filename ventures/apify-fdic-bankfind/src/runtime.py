"""Vendored support for standalone Git-subfolder builds; copies checked by tests."""
from __future__ import annotations
import asyncio
import hashlib
import os
import time
from datetime import datetime, timezone
import requests


class SourceError(ValueError):
    pass


class Client:
    """Serial, bounded public requests; no redirects, credentials or proxy rotation."""
    def __init__(self):
        self.last_request = 0.0

    def get(self, url, params=None):
        for attempt in range(2):
            time.sleep(max(0, 1.0 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            with requests.get(url, params=params, timeout=(10, 30), stream=True,
                              allow_redirects=False,
                              headers={'User-Agent': 'AndersonDataTools-PublicAPI/1.0 (+https://github.com/benjaminanderson0802/glacier-lean)',
                                       'Accept': 'application/json,text/plain'}) as response:
                if response.status_code in (429, 503) and attempt == 0:
                    retry = response.headers.get('Retry-After', '2')
                    if retry.isdigit() and int(retry) <= 30:
                        time.sleep(max(2, int(retry)))
                        continue
                if response.status_code != 200:
                    raise SourceError(f'Official source HTTP {response.status_code}; try again later.')
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 5_000_000:
                        raise SourceError('Official response exceeded 5 MB limit.')
                    chunks.append(chunk)
                return b''.join(chunks).decode('utf-8-sig'), response.url, dict(response.headers)
        raise SourceError('Official source unavailable.')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def provenance(text, url, headers):
    return {'source_url': url, 'retrieved_at': stamp(),
            'source_last_modified': headers.get('Last-Modified', headers.get('last-modified')),
            'source_sha256': hashlib.sha256(text.encode()).hexdigest()}


def uncertain(message, source_url, **extra):
    return {'outcome': 'uncertain', 'billable': False, 'message': message,
            'source_url': source_url, 'retrieved_at': stamp(), **extra}


def bounded_int(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer from {low} to {high}.')
    return value


async def deliver(actor, rows, event):
    """Recall Actor pattern: write evidence, then charge only validated source rows.

    Configure ONLY the custom event: synthetic start/dataset events would bill errors.
    Idempotency is scoped to the SDK/platform window, not a cross-run guarantee.
    """
    billing = os.getenv('APIFY_IS_AT_HOME') == '1'
    delivered = 0
    for index, row in enumerate(rows):
        if billing and row.get('billable') and actor.get_charging_manager().is_event_charge_limit_reached(event):
            break
        await actor.push_data(row)
        delivered += 1
        if billing and row.get('billable') and row.get('outcome') == 'ok':
            key = hashlib.sha256(f"{os.getenv('APIFY_ACTOR_RUN_ID', 'local')}:{event}:{index}:{row.get('record_id', '')}".encode()).hexdigest()
            charged = await actor.charge(event_name=event, count=1, idempotency_key=key)
            if charged.event_charge_limit_reached:
                break
    await actor.set_status_message(f'Delivered {delivered} rows; {sum(r["outcome"] == "uncertain" for r in rows)} uncertain source results. Check dataset details.', is_terminal=True)


async def run(collect, event):
    from apify import Actor
    async with Actor:
        inputs = await Actor.get_input() or {}
        rows = await asyncio.to_thread(collect, inputs)
        await deliver(Actor, rows, event)
