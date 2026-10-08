import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

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
  const file = ts.createSourceFile(path, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const report = (node, kind, value) => {
    const text = value.trim().replace(/\\s+/g, ' ')
    if (/[A-Za-z]/.test(text) && !allow.has(text)) {
      const pos = file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1
      findings.push(`${path}:${pos}: ${kind} ${JSON.stringify(text)}`)
    }
  }
  const visit = node => {
    if (ts.isJsxText(node)) report(node, 'JSX text', node.text)
    if (ts.isJsxAttribute(node) && node.initializer && ts.isStringLiteral(node.initializer) && ['title', 'sub', 'placeholder', 'aria-label', 'label'].includes(node.name.getText(file))) report(node, node.name.getText(file), node.initializer.text)
    ts.forEachChild(node, visit)
  }
  visit(file)
}
for (const root of roots) walk(root)
if (findings.length) console.log(`i18n scanner: ${findings.length} finding(s)\\n${findings.join('\\n')}`)
else console.log('i18n scanner: no findings')
if (process.argv.includes('--fail') && findings.length) process.exitCode = 1
