"""Operational smoke proof: real disposable Glacier, no approvals or live connectors.

This is not an acceptance test. It records actual run states, including unexecuted
steps behind owner gates. The independent acceptance suites remain unchanged.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from ventures import install_all as installer


def prove(output: Path, only: str | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    # Never touch an owner's home. Retain the disposable databases for inspection.
    home = Path(tempfile.mkdtemp(prefix='glacier-venture-proof-')).resolve()
    token = secrets.token_hex(32)
    (home / '.engine-token').write_text(token, encoding='utf-8')
    (home / '.engine-token').chmod(0o600)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    api = f'http://127.0.0.1:{port}'
    env = dict(os.environ, GLACIER_HOME=str(home), GLACIER_TOKEN=token,
               GLACIER_OLLAMA_URL='http://127.0.0.1:9', GLACIER_ALERT_URLS='',
               GIT_AUTHOR_NAME='Glacier proof', GIT_AUTHOR_EMAIL='proof@localhost',
               GIT_COMMITTER_NAME='Glacier proof', GIT_COMMITTER_EMAIL='proof@localhost')
    # A synthetic CSV exercises the ordinary freight intake without API access.
    incoming = home / 'ventures/freight-claims/incoming'
    incoming.mkdir(parents=True)
    shutil.copy2(REPO / 'ventures/freight-claims/tests/fixtures/shipstation-shipments.csv',
                 incoming / 'shipstation-shipments.csv')
    fixtures = {
        'coop-postcards/intake/jobber.json': 'coop-postcards/fixtures/jobber_completed_job.json',
        'job-closeout/incoming/jobber.json': 'job-closeout/tests/fixtures/jobber_completed_job.json',
        'osha-filing/incoming/summary.csv': 'osha-filing/fixtures/ita-establishments.example.csv',
        'freight-claims/incoming/owner-approved-authorization.pdf': 'blocks/reader/samples/documents/sample-bill-of-lading.pdf',
    }
    for destination, source in fixtures.items():
        target = home / 'ventures' / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / 'ventures' / source, target)
    for name, data in {
        'recovery.json': {'claim_id': 'fixture-claim', 'recovered_amount': '100.00', 'share_percent': '25'},
        'signer.json': {'name': 'Synthetic Shipper', 'email': 'shipper@example.test'},
        'receipt.json': {'claim_id': 'fixture-claim', 'carrier_received_date': '2026-10-01',
                         'reference': 'SYNTHETIC-ONLY',
                         'confirmation_document': str(REPO / 'ventures/freight-claims/tests/fixtures/delivery-receipt.txt')},
    }.items():
        (incoming / name).write_text(json.dumps(data), encoding='utf-8')
    report = {'scope': 'real Linux Glacier, synthetic local inputs, no approval decisions; commands behind gates remain unexecuted',
              'home': str(home), 'api': api, 'flows': [], 'errors': []}
    with (output / 'backend.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1',
                                    '--port', str(port)], cwd=REPO / 'glacier/backend', env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('proof engine stopped; see backend.log')
                try:
                    installer.api_json(api, token, '/api/environments')
                    break
                except OSError:
                    time.sleep(.2)
            else:
                raise TimeoutError('proof engine did not start within 120 seconds')
            installed = installer.install(api, token, only, home=home, ready_only=True)
            report['installed'] = installed
            repeated = installer.install(api, token, only, home=home, ready_only=True)
            report['unchanged_on_second_install'] = all(r['result'].get('unchanged') for r in repeated)
            if not report['unchanged_on_second_install']:
                report['errors'].append('second install changed environments')
            # Check the alert path before adding the full set of flow runs to Home.
            # Deliberately remove a schedule in this disposable engine. The genuine
            # canary must fail and Home must show its run as an alert.
            target = next(r for r in installed if not r['flow'].startswith('venture-health-'))
            graph = installer.api_json(api, token, f"/api/environments/{target['flow']}")
            broken = dict(graph, nodes=[n for n in graph['nodes'] if n['type'] != 'schedule'])
            installer.register_flow(api, token, broken)
            canary_id = f"venture-health-{target['venture']}"
            started = installer.start_once(api, token, canary_id)
            failed = wait_run(api, token, started['run_id'])
            home_view = installer.api_json(api, token, '/api/home', timeout=120)
            visible = any(item.get('kind') == 'failed_run' and item.get('ref', {}).get('run_id') == failed['run_id']
                          for item in home_view['needs_you'])
            report['failure_alert'] = {'run_id': failed['run_id'], 'status': failed['status'], 'visible_on_home': visible}
            if failed['status'] != 'failed' or not visible:
                report['errors'].append('injected failure did not produce a Home alert')
            installer.register_flow(api, token, graph)
            # Run serially so canaries observe settled states and resource use stays small.
            ordered = sorted(installed, key=lambda r: r['flow'].startswith('venture-health-'))
            for row in ordered:
                graph = installer.api_json(api, token, f"/api/environments/{row['flow']}")
                started = installer.start_once(api, token, row['flow'])
                run = wait_run(api, token, started['run_id'])
                record = {'venture': row['venture'], 'flow': row['flow'], 'run_id': run['run_id'],
                          'status': run['status'], 'waiting_on': run.get('waiting_on'),
                          'verified': run.get('verified'), 'node_states': run['node_states'],
                          'verification': run.get('verification'),
                          'unexecuted': [n['id'] for n in graph['nodes']
                                         if run['node_states'].get(n['id']) != 'done'],
                          'schedule': next(n['config'] for n in graph['nodes'] if n['type'] == 'schedule')}
                report['flows'].append(record)
                if run['status'] not in ('done', 'waiting') or 'failed' in run['node_states'].values():
                    report['errors'].append(f"{row['flow']}: {run['status']}")
                print(f"{row['flow']}: {run['status']} {run.get('waiting_on') or ''}", flush=True)
        except Exception as exc:
            report['errors'].append(f'{type(exc).__name__}: {exc}')
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()  # only the process created by this proof
                process.wait(timeout=10)
            (output / 'proof.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def wait_run(api: str, token: str, run_id: str) -> dict:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        run = installer.api_json(api, token, f'/api/runs/{run_id}')
        if run['status'] in ('done', 'waiting', 'failed', 'rejected'):
            return run
        time.sleep(.2)
    raise TimeoutError(f'run did not settle: {run_id}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--only')
    args = parser.parse_args()
    result = prove(args.output.resolve(), args.only)
    print(json.dumps({'proof': str(args.output / 'proof.json'), 'errors': result['errors']}, indent=2))
    raise SystemExit(bool(result['errors']))
