// Check that bold labels in the first-time tutorials still appear in screen source.
import { readFile, readdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const guide = path.join(root, '..', 'docs/guide')
const tutorials = [
  '01-first-automation.md',
  '02-ask-for-automation.md',
  '03-add-memory.md',
  '04-claims.md',
  '05-undo.md',
]
const sources = path.join(root, 'web/src')

const labels = new Set()
for (const name of tutorials) {
  const text = await readFile(path.join(guide, name), 'utf8')
  for (const match of text.matchAll(/\*\*([^*\n]+)\*\*/g)) labels.add(match[1])
}

async function sourceText(dir) {
  const pieces = []
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name)
    if (entry.isDirectory()) pieces.push(await sourceText(file))
    else if (/\.(tsx?|jsx?)$/.test(entry.name)) pieces.push(await readFile(file, 'utf8'))
  }
  return pieces.join('\n')
}

const source = await sourceText(sources)
const missing = [...labels].filter(label => !source.includes(label)).sort()
if (missing.length) {
  console.error('Guide labels missing from glacier/web/src:')
  for (const label of missing) console.error(`- ${label}`)
  process.exitCode = 1
} else {
  console.log(`PASS (${labels.size} bold tutorial labels found in glacier/web/src)`)
}
