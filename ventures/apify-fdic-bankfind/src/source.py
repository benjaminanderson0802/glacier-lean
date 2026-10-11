"""Official FDIC institutions endpoint, with source vintage and bounded pagination."""
import json
import re
from datetime import datetime
from .runtime import Client, SourceError, bounded_int, provenance, uncertain

URL = 'https://api.fdic.gov/banks/institutions'
FIELDS = 'CERT,NAME,ACTIVE,STALP,CITY,ZIP,DATEUPDT,WEBADDR'


def collect(inputs, client=None):
    cert, state = inputs.get('certificate'), inputs.get('state')
    if cert is not None and (not isinstance(cert, str) or not re.fullmatch(r'[0-9]{1,6}', cert)):
        raise ValueError('certificate must be a string of 1–6 digits.')
    if state is not None and (not isinstance(state, str) or not re.fullmatch(r'[A-Z]{2}', state)):
        raise ValueError('state must be a two-letter uppercase state abbreviation.')
    if not cert and not state:
        raise ValueError('Provide certificate or state.')
    maximum = bounded_int(inputs.get('max_records', 100), 'max_records', 1, 1000)
    page_size = bounded_int(inputs.get('page_size', 100), 'page_size', 1, 100)
    active = inputs.get('active_only', False)
    if type(active) is not bool:
        raise ValueError('active_only must be boolean.')
    filters = ([f'CERT:{int(cert)}'] if cert else []) + ([f'STALP:{state}'] if state else [])
    if active:
        filters.append('ACTIVE:1')
    client, rows, seen, offset, vintage = client or Client(), [], set(), 0, None
    try:
        while offset < maximum:
            text, url, headers = client.get(URL, {'filters': ' AND '.join(filters), 'fields': FIELDS,
                'format': 'json', 'sort_by': 'CERT', 'sort_order': 'ASC',
                'limit': min(page_size, maximum - offset), 'offset': offset})
            data = json.loads(text)
            total = data['meta']['total']
            batch = data['data']
            current_vintage = data['meta']['index']['name']
            if type(total) is not int or total < 0 or not isinstance(batch, list):
                raise SourceError('Invalid FDIC envelope.')
            if vintage is not None and vintage != current_vintage:
                raise SourceError('FDIC vintage changed while paging.')
            vintage = current_vintage
            if offset + len(batch) > total or len(batch) > min(page_size, maximum - offset) or (not batch and offset < total):
                raise SourceError('Incomplete FDIC page.')
            for item in batch:
                bank = item['data']
                identifier = str(bank['CERT'])
                if identifier in seen or not identifier.isdigit() or not bank['NAME'] or bank['ACTIVE'] not in (0, 1):
                    raise SourceError('Invalid or repeated FDIC institution.')
                if cert and int(identifier) != int(cert):
                    raise SourceError('FDIC returned a different certificate.')
                if state and bank['STALP'] != state:
                    raise SourceError('FDIC returned a different state.')
                if active and bank['ACTIVE'] != 1:
                    raise SourceError('FDIC returned an inactive institution.')
                seen.add(identifier)
                raw_date = bank.get('DATEUPDT')
                updated = datetime.strptime(raw_date, '%m/%d/%Y').date().isoformat() if raw_date else None
                rows.append({'record_id': identifier, 'outcome': 'ok', 'billable': True,
                    'message': 'Official institution record; not a bank safety or deposit coverage determination.',
                    'certificate': identifier, 'name': bank['NAME'], 'active': bank['ACTIVE'] == 1,
                    'state': bank.get('STALP'), 'city': bank.get('CITY'), 'postal_code': bank.get('ZIP'),
                    'website': bank.get('WEBADDR'), 'source_updated_at': updated, 'source_vintage': vintage,
                    'source_total': total, 'truncated': total > maximum,
                    'record_url': f'https://banks.data.fdic.gov/bankfind-suite/bankfind/details/{identifier}',
                    **provenance(text, url, headers)})
            offset += len(batch)
            if offset >= total:
                break
        if rows:
            return rows
        source = provenance(text, url, headers)
        as_of = source['retrieved_at'][:10]
        return [{'outcome': 'no_match', 'billable': False,
                 'message': f'No match found in FDIC as of {as_of}; no institution matched these filters in this source snapshot.',
                 **source}]
    except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
        # Fail the whole snapshot closed rather than sell an incomplete result set.
        return [uncertain(f'FDIC source unavailable or unexpected response ({type(exc).__name__}); retry later.', URL)]
    except Exception as exc:
        # HTTP library connection/timeout failures must not become paid empty matches.
        return [uncertain(f'FDIC request failed ({type(exc).__name__}); retry later.', URL)]
