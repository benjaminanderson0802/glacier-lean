"""Census state BPS monthly bulk files, comparing observed periods, not revisions."""
import csv
import io
import re
from datetime import datetime
from .runtime import Client, SourceError, provenance, uncertain

URL = 'https://www2.census.gov/econ/bps/State/'


def period(value):
    if not isinstance(value, str) or not re.fullmatch(r'20[0-9]{2}-(0[1-9]|1[0-2])', value):
        raise ValueError('period must be YYYY-MM, 2000–2099.')
    return value


def parse(text, expected):
    lines = list(csv.reader(io.StringIO(text)))
    if len(lines) < 4 or lines[0][:5] != ['Survey', 'FIPS', 'Region', 'Division', 'State'] or [v.strip() for v in lines[1]][:8] != ['Date', 'State', 'Code', 'Code', 'Name', 'Bldgs', 'Units', 'Value']:
        raise SourceError('Census CSV headers changed.')
    groups = ['1-unit', '2-units', '3-4 units', '5+ units',
              '1-unit rep', '2-units rep', '3-4 units rep', '5+ units rep']
    if [v.strip() for v in lines[0][6::3]] != groups or [v.strip() for v in lines[1][5:]] != ['Bldgs', 'Units', 'Value'] * 8:
        raise SourceError('Census metric columns changed.')
    rows = {}
    for line in lines[2:]:
        if not line or not ''.join(line).strip():
            continue
        cells = [c.strip() for c in line]
        if len(cells) != 29 or cells[0] != expected.replace('-', ''):
            raise SourceError('Unexpected Census row or survey date.')
        # Regional/division/US aggregate records have no state FIPS code.
        if not re.fullmatch(r'[0-9]{2}', cells[1]):
            continue
        if cells[1] in rows:
            raise SourceError('Duplicate Census state.')
        values = [int(v) if re.fullmatch(r'[0-9]+', v) else None for v in cells[5:]]
        rows[cells[1]] = {'name': cells[4], 'values': values}
    if len(rows) != 51:
        raise SourceError('Expected 50 states and DC; incomplete Census file.')
    return rows


def collect(inputs, client=None):
    current = inputs.get('period', 'latest')
    if current != 'latest':
        period(current)
    previous = inputs.get('previous_period')
    if previous is not None:
        period(previous)
    states = inputs.get('states', [])
    if not isinstance(states, list) or len(states) > 51 or not all(isinstance(s, str) and re.fullmatch(r'[0-9]{2}', s) for s in states):
        raise ValueError('states must be an array of up to 51 two-digit FIPS strings; empty means all states and DC.')
    client = client or Client()
    try:
        if current == 'latest':
            directory, _, _ = client.get(URL)
            candidates = re.findall(r'href="st([0-9]{2})([0-9]{2})c\.txt"', directory)
            valid = sorted({f'20{y}-{m}' for y, m in candidates if 1 <= int(m) <= 12 and f'20{y}-{m}' <= datetime.now().strftime('%Y-%m')})
            if not valid:
                raise SourceError('No monthly Census releases listed.')
            current = valid[-1]
        if previous is None:
            year, month = map(int, current.split('-'))
            previous = f'{year if month > 1 else year - 1:04d}-{month - 1 if month > 1 else 12:02d}'
        if previous >= current:
            raise SourceError('previous_period must precede period.')
        snapshots = []
        for value in (current, previous):
            text, url, headers = client.get(URL + 'st' + value[2:].replace('-', '') + 'c.txt')
            snapshots.append((parse(text, value), provenance(text, url, headers)))
        now, old = snapshots
        rows = []
        for state in sorted(set(states) if states else now[0]):
            if state not in now[0] or state not in old[0]:
                rows.append(uncertain('State missing from one or both releases; no zero substituted.', now[1]['source_url'], state_fips=state))
                continue
            a, b = now[0][state], old[0][state]
            if any(v is None for v in a['values'] + b['values']):
                rows.append(uncertain('Missing or nonnumeric source value; no zero substituted.', now[1]['source_url'], state_fips=state))
                continue
            units = sum(a['values'][1:12:3])
            old_units = sum(b['values'][1:12:3])
            value = sum(a['values'][2:12:3]) * 1000
            old_value = sum(b['values'][2:12:3]) * 1000
            rows.append({'record_id': f'{state}:{current}:{previous}', 'state_fips': state, 'name': a['name'],
                'outcome': 'ok', 'billable': True, 'message': 'Period-to-period change in estimates including imputation; not individual permit leads or a revision flag.',
                'period': current, 'previous_period': previous, 'units': units, 'previous_units': old_units,
                'units_change': units - old_units, 'units_change_pct': round(100 * (units - old_units) / old_units, 4) if old_units else None,
                'valuation_usd': value, 'previous_valuation_usd': old_value, 'valuation_change_usd': value - old_value,
                'reported_units': sum(a['values'][13:24:3]),
                'previous_source_url': old[1]['source_url'], 'previous_source_sha256': old[1]['source_sha256'],
                'previous_source_last_modified': old[1]['source_last_modified'], **now[1]})
        return rows
    except Exception as exc:
        return [uncertain(f'Census release unavailable or unexpected response ({type(exc).__name__}); please check source.', URL)]
