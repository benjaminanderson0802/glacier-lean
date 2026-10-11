"""Ordinary unit tests for installer glue; independent acceptance stays in ventures/tests."""
import json
from unittest.mock import patch

import pytest
from ventures import install_all as installer


def test_ready_selection_excludes_drafts(tmp_path, monkeypatch):
    for slug, status in [('live', 'ready'), ('draft', 'in_progress'), ('hold', 'on_hold')]:
        folder = tmp_path / slug
        folder.mkdir()
        (folder / 'venture.json').write_text(json.dumps({'slug': slug, 'status': status}))
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    assert [p.parent.name for p in installer.manifests(ready_only=True)] == ['live']
    with pytest.raises(ValueError, match='ready'):
        installer.manifests('draft', ready_only=True)


def test_schedule_adds_one_entry_without_mutating_original_or_checks():
    source = {'id': 'x', 'nodes': [{'id': 'gate', 'type': 'approval'}], 'edges': [],
              'max_steps': 1, 'acceptance': [{'kind': 'human', 'prompt': 'Review'}]}
    result = installer.scheduled_flow(source)
    assert source['max_steps'] == 1
    assert result['max_steps'] == 2
    assert result['acceptance'] == source['acceptance']
    assert result['edges'][0]['target'] == 'gate'
    assert installer.scheduled_flow(result) == result
    cfg = result['nodes'][0]['config']
    assert cfg['overlap'] == 'skip' and cfg['missed_run'] == 'run_once'


def test_start_respects_pause_and_waiting_run():
    with patch.object(installer, 'api_json', return_value={'enabled': False}) as api:
        assert installer.start_once('http://localhost', 't', 'flow')['state'] == 'paused'
        assert api.call_count == 1
    with patch.object(installer, 'api_json', side_effect=[{'enabled': True}, [{'status': 'waiting', 'run_id': 'r'}]]) as api:
        assert installer.start_once('http://localhost', 't', 'flow')['run_id'] == 'r'
        assert api.call_count == 2


def test_reinstall_preserves_owner_pause():
    flow = {'id': 'x', 'nodes': [], 'edges': []}
    current = dict(flow, enabled=False)
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self): return json.dumps(current).encode()
    with patch.object(installer, 'urlopen', return_value=Response()), patch.object(installer, 'register_flow') as put:
        assert installer.register_flow_if_changed('http://localhost', 't', flow)['unchanged']
        put.assert_not_called()
    assert 'enabled' not in flow


def test_health_canary_reports_missing_schedule_and_failed_run(tmp_path, monkeypatch):
    venture = tmp_path / 'sample'
    venture.mkdir()
    manifest = {'slug': 'sample', 'status': 'ready', 'flows': ['missing-schedule', 'failed']}
    (venture / 'venture.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    with patch.object(installer, 'api_json', side_effect=[
        {'nodes': []},
        {'nodes': [{'type': 'schedule', 'config': {'cron': '0 7 * * *'}}]},
        [{'run_id': 'r', 'status': 'failed', 'started_at': '2026-10-10T00:00:00+00:00'}],
    ]):
        report = installer.health_canary('http://localhost', 't', 'sample')
    assert not report['healthy']
    assert len(report['problems']) == 2
    assert 'schedule missing' in report['problems'][0]
    assert 'failed' in report['problems'][1]


def test_health_canary_distinguishes_waiting_from_overdue(tmp_path, monkeypatch):
    venture = tmp_path / 'sample'
    venture.mkdir()
    (venture / 'venture.json').write_text(json.dumps({'slug': 'sample', 'status': 'ready', 'flows': ['flow']}))
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    graph = {'nodes': [{'type': 'schedule', 'config': {'cron': '0 7 * * *'}}]}
    for status, healthy in [('waiting', True), ('done', False)]:
        with patch.object(installer, 'api_json', side_effect=[graph, [
            {'run_id': 'r', 'status': status, 'started_at': '2020-01-01T00:00:00+00:00'}
        ]]):
            report = installer.health_canary('http://localhost', 't', 'sample')
        assert report['healthy'] is healthy


def test_binding_handles_compound_shell_commands(tmp_path):
    import subprocess
    from pathlib import Path
    flow = {'id': 'compound', 'nodes': [{'type': 'command', 'config': {
        'cmd': 'if true; then python -c "print(42)"; fi'}}], 'edges': []}
    bound = installer._runtime_flow(flow, repo_root=Path.cwd(), slug='sample', home=tmp_path)
    from glacier.backend.shell_commands import command_invocation
    argv, shell, _warning = command_invocation(bound['nodes'][0]['config']['cmd'])
    result = subprocess.run(argv, shell=shell, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '42'
