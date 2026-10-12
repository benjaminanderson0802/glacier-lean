// Ordinary unit tests for shell routing; independent e2e acceptance stays tester-owned.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { roomNeedPath, roomRunPath, roomTeamPath } from './roomLinks.ts'

test('room links preserve identifiers containing route delimiters and Unicode', () => {
  const env = 'weekly/report # café', run = 'run/2?'
  const path = roomRunPath(env, run).split('/').map(decodeURIComponent)
  assert.deepEqual(path, ['automations', 'flow', env, run])
  assert.equal(decodeURIComponent(roomTeamPath('team/a #1').split('/')[2]), 'team/a #1')
})

test('owner items route to their claim, complete run reference, or owner inbox', () => {
  assert.equal(roomNeedPath({ ref: { claim_id: 'review/one' } }), 'home/claim/review%2Fone')
  assert.equal(roomNeedPath({ ref: { env_id: 'daily', run_id: 'run1' } }), 'automations/flow/daily/run1')
  for (const ref of [{}, { run_id: 'orphan' }, { env_id: 'daily' }, { venture_slug: 'venture', step_id: 'setup' }]) {
    assert.equal(roomNeedPath({ ref }), 'home')
  }
})
