"""Exact-ID NPPES lookups; presence is not credentialing or licensure verification."""
import json
import re
from .runtime import Client, SourceError, provenance, uncertain

URL = 'https://npiregistry.cms.hhs.gov/api/'


def valid_npi(value):
    if not isinstance(value, str) or not re.fullmatch(r'[12][0-9]{9}', value):
        return False
    digits = [int(c) for c in '80840' + value]
    return sum((d * 2 - 9 if d * 2 > 9 else d * 2) if i % 2 else d
               for i, d in enumerate(reversed(digits))) % 10 == 0


def collect(inputs, client=None):
    npis = inputs.get('npis')
    if not isinstance(npis, list) or not 1 <= len(npis) <= 50 or not all(valid_npi(n) for n in npis):
        raise ValueError('npis must contain 1–50 ten-digit NPI strings with valid check digits.')
    client, rows = client or Client(), []
    for npi in dict.fromkeys(npis):
        try:
            text, url, headers = client.get(URL, {'version': '2.1', 'number': npi})
            payload = json.loads(text)
            if 'Errors' in payload or type(payload.get('result_count')) is not int:
                raise SourceError('NPPES API error or changed schema.')
            found = payload['results']
            if not isinstance(found, list) or len(found) != payload['result_count'] or len(found) > 1:
                raise SourceError('NPPES count mismatch.')
            if not found:
                rows.append({'record_id': npi, 'npi': npi, 'outcome': 'no_match', 'billable': False,
                    'message': 'No public NPPES record returned for this NPI at retrieval time; not proof of invalid credentials.',
                    **provenance(text, url, headers)})
                continue
            provider = found[0]
            basic = provider['basic']
            if str(provider['number']) != npi or provider['enumeration_type'] not in ('NPI-1', 'NPI-2'):
                raise SourceError('NPPES identity mismatch.')
            name = basic.get('organization_name') or ' '.join(filter(None, [basic.get('first_name'), basic.get('middle_name'), basic.get('last_name')]))
            if not name or basic.get('status') not in ('A', 'D'):
                raise SourceError('Missing provider name/status.')
            locations = [a for a in provider['addresses'] if a.get('address_purpose') == 'LOCATION']
            primary = [t for t in provider['taxonomies'] if t.get('primary') is True]
            address = locations[0] if locations else {}
            taxonomy = primary[0] if len(primary) == 1 else {}
            rows.append({'record_id': npi, 'npi': npi, 'outcome': 'ok', 'billable': True,
                'message': 'Public NPPES registry record only; not license, exclusion or credential verification.',
                'name': name, 'enumeration_type': provider['enumeration_type'], 'registry_status': basic['status'],
                'source_updated_at': basic.get('last_updated'), 'enumeration_date': basic.get('enumeration_date'),
                'taxonomy_code': taxonomy.get('code'), 'taxonomy_description': taxonomy.get('desc'),
                'address': address.get('address_1'), 'address_2': address.get('address_2'),
                'city': address.get('city'), 'state': address.get('state'), 'postal_code': address.get('postal_code'),
                'country_code': address.get('country_code'),
                'warnings': ([] if locations else ['No practice address in source.']) + ([] if len(primary) == 1 else ['No unique primary taxonomy in source.']),
                'record_url': f'https://npiregistry.cms.hhs.gov/provider-view/{npi}',
                **provenance(text, url, headers)})
        except Exception as exc:
            rows.append(uncertain(f'NPPES unavailable or unexpected response ({type(exc).__name__}); please check source.', URL, record_id=npi, npi=npi))
    return rows
