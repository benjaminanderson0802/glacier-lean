// Regenerate sprite assets and fail if the committed PNGs do not match pixel for pixel.
import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readdirSync, rmSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const venvPython = path.resolve(web, '../..', process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python')
const python = process.env.PYTHON ?? (existsSync(venvPython) ? venvPython : process.platform === 'win32' ? 'python' : 'python3')
const temp = mkdtempSync(path.join(os.tmpdir(), 'glacier-sprites-'))
// Compare decoded pixels, not file bytes: PNG compression differs between Pillow/zlib builds.
const compare = `
import sys
from PIL import Image
a, b, names = sys.argv[1], sys.argv[2], sys.argv[3:]
for n in names:
    x = Image.open(f"{a}/{n}").convert("RGBA"); y = Image.open(f"{b}/{n}").convert("RGBA")
    if x.size != y.size or x.tobytes() != y.tobytes():
        sys.exit(f"sprite differs: {n}")
`
try {
  const run = spawnSync(python, [path.resolve(web, '../../tools/pixelart/make_sprites.py'), temp], { encoding: 'utf8' })
  if (run.status !== 0) throw new Error(run.error?.message || run.stderr || run.stdout || 'sprite generation failed')
  const committed = path.join(web, 'src/theme/sprites')
  const names = readdirSync(committed).filter(n => n.endsWith('.png')).sort()
  const generated = readdirSync(temp).filter(n => n.endsWith('.png')).sort()
  if (names.join('\n') !== generated.join('\n')) throw new Error('sprite filename set differs')
  const check = spawnSync(python, ['-c', compare, committed, temp, ...names], { encoding: 'utf8' })
  if (check.status !== 0) throw new Error(check.error?.message || check.stderr || 'sprite comparison failed')
  console.log(`sprite identity ok (${names.length} PNGs)`)
} finally { rmSync(temp, { recursive: true, force: true }) }
