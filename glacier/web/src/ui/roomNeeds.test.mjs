import test from 'node:test'
import assert from 'node:assert/strict'
import { roomApprovalsMissingFromNeedsYou } from './roomNeeds.ts'

const home = (needs_you, running) => ({ needs_you, running })
const approval = run_id => ({ kind: 'approval', title: 'approval waiting', detail: 'review', at: '', ref: { run_id } })
const run = (run_id, status = 'waiting') => ({ run_id, env_id: 'flow', name: run_id, status, step: 0, steps: 1, started_at: '' })

test('waiting runs omitted by the capped needs-you list remain visible in the room', () => {
  assert.deepEqual(roomApprovalsMissingFromNeedsYou(home([], [run('waiting')])).map(item => item.run_id), ['waiting'])
})

test('listed approvals are not duplicated and non-waiting runs are excluded', () => {
  assert.deepEqual(roomApprovalsMissingFromNeedsYou(home([approval('listed')], [run('listed'), run('active', 'running')])), [])
  assert.deepEqual(roomApprovalsMissingFromNeedsYou(null), [])
})
