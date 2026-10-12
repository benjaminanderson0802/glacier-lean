"""Ordinary unit regressions for PH5 task execution; not the acceptance board."""
import teams


def plan():
    return {
        'vision': {'goal': 'Write a result', 'done': ['result.txt exists']},
        'spec': {'requirements': ['Write a result'], 'out_of_scope': [],
                 'acceptance': [{'kind': 'command', 'cmd': 'test -f result.txt'}]},
        'features': [{'id': 'result', 'title': 'Result'}],
        'team': {'worker_mode': 'parallel', 'parallel_limit': 3, 'engine': 'codex',
                 'roles': [{'id': 'builder', 'charter': 'Write the result'}]},
        'tasks': [{'id': 'write', 'title': 'Write result', 'role': 'builder',
                   'requires_approval': True, 'depends_on': [],
                   'acceptance': [{'kind': 'command', 'cmd': 'test -f result.txt'}]}],
    }


def test_approval_gate_precedes_worker_and_creating_workspace(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(teams, '_worker', lambda *a: calls.append(a) or {'exit_code': 0})
    monkeypatch.setattr(teams, '_review', lambda *a: {'passed': True})
    monkeypatch.setattr(teams, '_check_task', lambda *a: {'passed': True})
    p = plan()
    workspace = tmp_path / 'not-created'
    result = teams.execute_task('team', 'write', p, p['tasks'][0], str(workspace),
                                {'tasks': {'write': {'status': 'pending', 'attempts': 0}}})
    assert result['status'] == 'awaiting_approval'
    assert calls == []
    assert not workspace.exists()


def test_recorded_approval_allows_one_execution_without_second_gate(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(teams, '_worker', lambda *a: calls.append(a) or {'exit_code': 0})
    monkeypatch.setattr(teams, '_review', lambda *a: {'passed': True})
    monkeypatch.setattr(teams, '_check_task', lambda *a: {'passed': True})
    monkeypatch.setattr(teams, '_relevant_memory', lambda *a: [])
    p = plan()
    result = teams.execute_task('team', 'write', p, p['tasks'][0], str(tmp_path),
                                {'tasks': {'write': {'approved': True}}})
    assert result['status'] == 'done'
    assert len(calls) == 1


def test_parallel_plan_final_workspace_is_merged_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv('GLACIER_HOME', str(tmp_path))
    teams.vault.init(str(tmp_path / 'vault'))
    teams.init(str(tmp_path / 'glacier.sqlite'))
    p = plan()
    vision = teams.create_vision(p['vision'])
    saved = teams.save_plan(p, vision['path'])
    row = teams._read(saved['team_id'])
    assert row['workspace'] == teams.runner.workspaces.base(str(tmp_path), f"team-{saved['team_id']}")


def test_retry_state_preserves_failure_evidence_and_retries_to_limit(tmp_path, monkeypatch):
    monkeypatch.setenv('GLACIER_HOME', str(tmp_path))
    teams.init(str(tmp_path / 'glacier.sqlite'))
    p = plan()
    p['team']['worker_mode'] = 'sequential'
    p['guards'] = {'max_retries': 2}
    p['tasks'][0]['requires_approval'] = False
    calls = []
    monkeypatch.setattr(teams, 'execute_task', lambda *a: calls.append(a) or
                        {'status': 'retry', 'output': 'failed check'})
    monkeypatch.setattr(teams, 'stuck_claim', lambda *a: 'claim-proof')
    result = teams.run_team_local('unit', p, str(tmp_path))
    assert len(calls) == 2
    assert result['status'] == 'needs_owner'
    assert result['tasks']['write']['status'] == 'needs_owner'
    assert result['tasks']['write']['claim_id'] == 'claim-proof'


def test_durable_coordinator_approves_once_and_checks_merged_output(tmp_path, monkeypatch):
    """Coordinator transitions with real worktree merges and fixture model calls."""
    from pathlib import Path
    monkeypatch.setenv('GLACIER_HOME', str(tmp_path))
    teams.vault.init(str(tmp_path / 'vault'))
    teams.init(str(tmp_path / 'glacier.sqlite'))
    p = plan()
    p['team']['roles'].append({'id': 'evaluator', 'charter': 'Inspect the result'})
    p['tasks'].append({'id': 'evaluate', 'title': 'Inspect result', 'role': 'evaluator',
                       'feature_id': 'result', 'depends_on': ['write'],
                       'acceptance': [{'kind': 'command', 'cmd': 'test -f result.txt'}]})
    saved = teams.save_plan(p, teams.create_vision(p['vision'])['path'])
    team_id = saved['team_id']
    calls, approvals = [], []

    def worker(context, workspace, task):
        calls.append(task['id'])
        result = Path(workspace) / 'result.txt'
        if task['id'] == 'write':
            assert approvals == ['write']
            result.write_text('verified')
        assert result.read_text() == 'verified'
        return {'output': 'checked file', 'exit_code': 0}

    def receive(**kwargs):
        row = teams._read(team_id)
        assert calls == []
        assert row['state']['tasks']['write']['attempts'] == 0
        approvals.append('write')
        return {'action': 'approve_task', 'task_id': 'write', 'approved': True}

    class Future:
        def __init__(self, value): self.value = value
        def get_result(self): return self.value

    monkeypatch.setattr(teams, '_worker', worker)
    monkeypatch.setattr(teams, '_relevant_memory', lambda *a: [])
    monkeypatch.setattr(teams, '_review', lambda *a: {'passed': True})
    monkeypatch.setattr(teams, '_govern', lambda *a: {'passed': True})
    monkeypatch.setattr(teams.DBOS, 'recv', receive)
    monkeypatch.setattr(teams.DBOS, 'start_workflow', lambda _, tid, task_id:
                        Future(teams.team_task_step.__wrapped__(tid, task_id)))
    assert teams.run_team.__wrapped__(team_id) == 'done'
    state = teams.get(team_id)
    assert calls == ['write', 'evaluate']
    assert state['tasks']['write']['attempts'] == 1
    assert state['features']['result']['status'] == 'passing'
    assert state['objective_check']['passed']


def test_spec_generation_schema_requires_same_ears_form_as_validator(monkeypatch):
    import re
    captured = {}
    def answer(prompt, engine, schema):
        captured.update(schema)
        return {'goal': 'Write a small result', 'requirements': ['The system shall create result.txt'],
                'acceptance': ['result.txt exists'], 'out_of_scope': []}
    monkeypatch.setattr(teams, 'ask_engine', answer)
    teams.draft_spec('Owner wants a local result', 'Use the confirmed brief')
    pattern = captured['properties']['requirements']['items']['pattern']
    assert re.match(pattern, 'The system shall create result.txt')
    assert not re.match(pattern, 'The builder shall create result.txt')


def test_supervisor_receives_independent_checks_alongside_handover(monkeypatch):
    import decider
    captured = {}
    def decide(question, options, context=''):
        captured.update(question=question, context=context)
        return {'choice': 'pass', 'engine': 'fixture'}
    monkeypatch.setattr(decider, 'decide', decide)
    p = plan()
    p['team']['supervisor'] = 'builder'
    checks = {'passed': True, 'evidence': ['Independent command verified exact file bytes']}
    teams._review(p, p['tasks'][0], 'Worker claims success', 1, checks)
    assert 'test -f result.txt' in captured['question']
    assert 'Independent command verified exact file bytes' in captured['context']


def test_independent_check_refuses_filesystem_roots_without_copying(tmp_path):
    check = {'kind': 'command', 'cmd': 'true'}
    result = teams._check_task({'acceptance': [check]}, '', teams.tempfile.gettempdir())
    assert result['passed'] is False
    assert 'unsafe workspace root' in result['evidence']
