// Theme guard: retro art uses only palette tokens, integer pixel sizing, sprite frames and Press Start 2P.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const src = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const TOKENS = path.join(src, 'theme/tokens.css')
const ALLOWLIST = path.join(path.dirname(fileURLToPath(import.meta.url)), 'theme_lint_allowlist.json')
const allowlist = JSON.parse(readFileSync(ALLOWLIST, 'utf8'))
const usedAllowlist = new Set()
const normalize = value => value.trim().replace(/\s+/g, ' ')
const allowedSizes = new Set(['calc(8 * var(--px))', 'calc(16 * var(--px))'])
const tokenText = readFileSync(TOKENS, 'utf8')
const sizeTokens = new Set([...tokenText.matchAll(/(--g-size-[\w-]+)\s*:\s*(calc\((?:8|16)\s*\*\s*var\(--px\)\))/g)].map(m => `var(${m[1]})`))
const isAllowedSize = value => allowedSizes.has(normalize(value)) || sizeTokens.has(normalize(value))
const isAllowedFont = value => {
  const normalized = normalize(value)
  if (normalized === 'inherit') return true
  return [...allowedSizes, ...sizeTokens].some(size => normalized === size || normalized.startsWith(`${size}/`) || normalized.startsWith(`${size} `))
}
const files = []
const walk = d => readdirSync(d).forEach(f => { const p = path.join(d, f); statSync(p).isDirectory() ? walk(p) : /\.(css|tsx?|mjs)$/.test(f) && files.push(p) })
walk(src)

const rules = [
  [/#[0-9a-fA-F]{3,8}\b(?![\w-]*['"]?\s*\])/g, 'raw hex colour (use a --g-* token)'],
  [/\b(rgba?|hsla?|oklch|lab)\(/g, 'raw colour function (use a --g-* token)'],
  [/font-family\s*:(?!\s*var\(--g-font)/g, 'font-family not from tokens'],
  [/box-shadow\s*:[^;]*(?:blur|\d+px\s+\d+px\s+\d+px)/gi, 'blurred box-shadow (use a solid pixel offset)'],
  [/fontFamily\s*:\s*['"`]/g, 'inline fontFamily not from tokens'],
  [/\b(Inter|Roboto|Helvetica|Arial|system-ui|-apple-system|Segoe UI|sans-serif)\b/g, 'generic UI font'],
  [/\bfonts\.googleapis|\bhttps?:\/\/(?!127\.0\.0\.1|localhost)[\w.-]+\.(com|net|io)\//g, 'remote asset (must be bundled for offline use)'],
]
const fails = []
for (const entry of allowlist) {
  if (!entry.file || !entry.property || !entry.value || !entry.reason?.trim()) fails.push('theme_lint_allowlist.json: every exception must name a file, property, value, and reason')
}
const checkSize = (file, property, value, lineNo, line) => {
  const normalized = normalize(value)
  if (property === 'font' ? isAllowedFont(normalized) : isAllowedSize(normalized)) return
  const relative = path.relative(src, file).split(path.sep).join('/')
  const entry = allowlist.find(item => item.file === relative && item.property === property && normalize(item.value) === normalized)
  if (entry) { usedAllowlist.add(entry); return }
  fails.push(`${relative}:${lineNo}: ${property} must use the 8px or 16px pixel size token\n    ${line.trim().slice(0, 140)}`)
}
for (const f of files) {
  if (f === TOKENS) continue
  const text = readFileSync(f, 'utf8')
  text.split('\n').forEach((line, i) => {
    if (/theme-lint-ignore/.test(line)) return
    for (const [re, why] of rules) { re.lastIndex = 0; if (re.test(line)) fails.push(`${path.relative(src, f)}:${i + 1}: ${why}\n    ${line.trim().slice(0, 140)}`) }
    for (const match of line.matchAll(/\bfont-size\s*:\s*([^;}]+)/g)) checkSize(f, 'font-size', match[1], i + 1, line)
    for (const match of line.matchAll(/\bfont\s*:\s*([^;}]+)/g)) checkSize(f, 'font', match[1], i + 1, line)
    for (const match of line.matchAll(/\bborder-radius\s*:\s*([^;}!]+)/g)) {
      if (!/^\s*0(?:px|%|em|rem)?\s*$/.test(match[1])) fails.push(`${path.relative(src, f)}:${i + 1}: border-radius is not allowed\n    ${line.trim().slice(0, 140)}`)
    }
  })
  if (path.relative(src, f).startsWith(`screens${path.sep}`) && /<svg\b[\s\S]*?<\/svg\s*>/i.test(text) && /<(?:line|polyline|polygon)\b|<path\b[^>]*\bstroke\s*=/i.test(text)) {
    fails.push(`${path.relative(src, f)}: SVG line icons in screens must use 8x8 pixel masks`)
  }
}
for (const entry of allowlist) if (!usedAllowlist.has(entry)) fails.push(`theme_lint_allowlist.json: unused exception for ${entry.file} ${entry.property}: ${entry.value}`)
if (fails.length) { console.error(`THEME LINT FAILED (${fails.length})\n` + fails.join('\n')); process.exit(1) }
const css = readFileSync(path.join(src, 'theme/ui.css'), 'utf8')
if (!css.includes("border-image: url('./sprites/frame-light.png')") || !css.includes('image-rendering: pixelated')) {
  console.error('THEME LINT FAILED (sprite frames and pixel rendering must be enabled)'); process.exit(1)
}
if (!css.includes('font: var(--g-size-body)/1.7 var(--g-font-body)')) { console.error('THEME LINT FAILED (Press Start 2P body font must come from the theme token)'); process.exit(1) }
if (!css.includes('border-radius: 0 !important') || !css.includes('box-shadow: none !important')) { console.error('THEME LINT FAILED (global pixel-square surfaces and solid shadows are required)'); process.exit(1) }
console.log(`theme lint ok (${files.length} files; ${usedAllowlist.size} documented existing typography exceptions)`)
