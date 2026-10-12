"""Run actual SDK entrypoints locally; never authenticate or start cloud runs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
for slug in ('fdic-bankfind', 'census-permits', 'npi-batch'):
    root = ROOT / 'ventures' / ('apify-' + slug)
    evidence = root / 'evidence'
    evidence.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='a-apify3-') as folder:
        storage = Path(folder)
        kv = storage / 'key_value_stores/default'
        kv.mkdir(parents=True)
        inputs = json.loads((root / 'example-input.json').read_text())
        (kv / 'INPUT.json').write_text(json.dumps(inputs))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('APIFY_', 'ACTOR_', 'CRAWLEE_'))}
        env.update(APIFY_IS_AT_HOME='0', APIFY_LOCAL_STORAGE_DIR=str(storage), CRAWLEE_STORAGE_DIR=str(storage), CRAWLEE_PURGE_ON_START='false')
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run([sys.executable, '-m', 'src'], cwd=root, env=env, capture_output=True, text=True, timeout=180)
        (evidence / 'local-main.log').write_text(result.stdout + result.stderr)
        rows = [json.loads(p.read_text()) for p in sorted((storage / 'datasets/default').glob('*.json')) if not p.name.startswith('__')]
        # SDK storage metadata is not a dataset item.
        rows = [r for r in rows if isinstance(r, dict) and 'outcome' in r]
        output = {'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
                  'command': f'{sys.executable} -m src', 'cwd': str(root), 'mode': 'real SDK main; isolated local storage; no cloud billing',
                  'input': inputs, 'exit_code': result.returncode, 'rows': rows}
        (evidence / 'local-output.json').write_text(json.dumps(output, indent=2) + '\n')
        print(slug, 'exit', result.returncode, 'rows', len(rows), 'outcomes', [r['outcome'] for r in rows])
        if result.returncode or not rows or any(r['outcome'] != 'ok' for r in rows):
            print(result.stdout[-2000:], result.stderr[-2000:])
            raise SystemExit('Live source/entrypoint canary did not pass; inspect saved evidence.')
