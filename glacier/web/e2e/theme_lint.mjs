// Theme guard: the retro look lives ONLY in src/theme/tokens.css. Any other file that sets its own
// colour, font or corner radius fails the build. This is what keeps future work from drifting to a generic theme.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const src = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const TOKENS = path.join(src, 'theme/tokens.css')
const files = []
const walk = d => readdirSync(d).forEach(f => { const p = path.join(d, f); statSync(p).isDirectory() ? walk(p) : /\.(css|tsx?|mjs)$/.test(f) && files.push(p) })
walk(src)

const rules = [
  [/#[0-9a-fA-F]{3,8}\b(?![\w-]*['"]?\s*\])/g, 'raw hex colour (use a --g-* token)'],
  [/\b(rgba?|hsla?|oklch|lab)\(/g, 'raw colour function (use a --g-* token)'],
  [/font-family\s*:(?!\s*var\(--g-font)/g, 'font-family not from tokens'],
  [/fontFamily\s*:\s*['"`]/g, 'inline fontFamily not from tokens'],
  [/border-radius\s*:(?!\s*(var\(--g-radius|0\b|inherit))/g, 'border-radius not from tokens'],
  [/\b(Inter|Roboto|Helvetica|Arial|system-ui|-apple-system|Segoe UI|sans-serif)\b/g, 'generic UI font'],
  [/\bfonts\.googleapis|\bhttps?:\/\/(?!127\.0\.0\.1|localhost)[\w.-]+\.(com|net|io)\//g, 'remote asset (must be bundled for offline use)'],
]
const fails = []
for (const f of files) {
  if (f === TOKENS) continue
  const text = readFileSync(f, 'utf8')
  text.split('\n').forEach((line, i) => {
    if (/theme-lint-ignore/.test(line)) return
    for (const [re, why] of rules) { re.lastIndex = 0; if (re.test(line)) fails.push(`${path.relative(src, f)}:${i + 1}: ${why}\n    ${line.trim().slice(0, 140)}`) }
  })
}
if (fails.length) { console.error(`THEME LINT FAILED (${fails.length})\n` + fails.join('\n')); process.exit(1) }
console.log(`theme lint ok (${files.length} files)`)
