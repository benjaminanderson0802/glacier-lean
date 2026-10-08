import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
const roots = ['src/screens', 'src/ui']
const allowed = new Set(['…', '→', '·', '‹', '—', '•'])
const errors = []
function walk(dir) { for (const e of readdirSync(dir, { withFileTypes: true })) { const p = join(dir, e.name); if (e.isDirectory()) walk(p); else if (p.endsWith('.tsx')) check(p) } }
function check(path) {
  const s = readFileSync(path, 'utf8')
  // Remove comments and quoted/template strings outside JSX, then inspect JSX text spans.
  const stripped = s.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, m => ' '.repeat(m.length))
  const re = />([^<>]*[A-Za-z][^<>]*)</g
  for (const m of stripped.matchAll(re)) {
    const text = m[1].replace(/\s+/g, ' ').trim()
    if (!text || allowed.has(text) || text.includes('{') || text.includes('}') || /^\s*$/.test(text)) continue
    // This heuristic only reports simple literal text nodes, not code accidentally matched across tags.
    if (/^[\w ,.!?…→·‹—'’&:;()\-]+$/.test(text)) errors.push(`${path}: ${JSON.stringify(text)}`)
  }
}
for (const root of roots) walk(root)
if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1 } else console.log('i18n JSX text check passed')
