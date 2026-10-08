// Regenerate sprite assets and fail if the committed PNGs do not match.
import { spawnSync } from 'node:child_process'
import { mkdtempSync, readdirSync, readFileSync, rmSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const temp = mkdtempSync(path.join(os.tmpdir(), 'glacier-sprites-'))
try {
  const run = spawnSync(path.resolve(web, '../../.venv/bin/python'), [path.resolve(web, '../../tools/pixelart/make_sprites.py'), temp], { encoding: 'utf8' })
  if (run.status !== 0) throw new Error(run.stderr || run.stdout || 'sprite generation failed')
  const committed = path.join(web, 'src/theme/sprites')
  const names = readdirSync(committed).filter(n => n.endsWith('.png')).sort()
  const generated = readdirSync(temp).filter(n => n.endsWith('.png')).sort()
  if (names.join('\n') !== generated.join('\n')) throw new Error('sprite filename set differs')
  for (const name of names) if (!readFileSync(path.join(committed, name)).equals(readFileSync(path.join(temp, name)))) throw new Error(`sprite differs: ${name}`)
  console.log(`sprite identity ok (${names.length} PNGs)`)
} finally { rmSync(temp, { recursive: true, force: true }) }
