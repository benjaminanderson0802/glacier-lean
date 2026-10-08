import { readFileSync, readdirSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const base = fileURLToPath(new URL('../', import.meta.url))
const roots = ['src/screens', 'src/ui']
const allow = new Set(['…', '→', '·', '‹', '—', '•', '+'])
const findings = []
const walk = dir => readdirSync(join(base, dir), { withFileTypes: true }).forEach(entry => {
  const path = join(dir, entry.name)
  if (entry.isDirectory()) walk(path)
  else if (path.endsWith('.tsx')) scan(path)
})

function scan(path) {
  const source = readFileSync(join(base, path), 'utf8')
  // Visible prop literals: only the five user-facing props named in the card.
  const props = /\b(title|sub|placeholder|aria-label|label)\s*=\s*(["'])(.*?)\2/g
  for (const match of source.matchAll(props)) {
    const prefix = source.slice(Math.max(0, match.index - 2), match.index)
    const value = match[3].trim()
    if (!prefix.endsWith('{') && /[A-Za-z]/.test(value) && !allow.has(value)) findings.push(`${path}: ${match[1]}=${JSON.stringify(value)}`)
  }
  // Match direct JSX text nodes between tags. Expression boundaries exclude code fragments.
  const jsxText = />([^<>\n{}]*[A-Za-z][^<>\n{}]*)</g
  for (const match of source.matchAll(jsxText)) {
    const value = match[1].replace(/\s+/g, ' ').trim()
    if (!value || allow.has(value)) continue
    if (/^[\w ,.!?…→·‹—'’&:;()\-]+$/.test(value)) findings.push(`${path}: JSX text ${JSON.stringify(value)}`)
  }
}

for (const root of roots) walk(root)
if (findings.length) console.log(`i18n scanner: ${findings.length} finding(s)\n${findings.join('\n')}`)
else console.log('i18n scanner: no findings')
if (process.argv.includes('--fail') && findings.length) process.exitCode = 1
