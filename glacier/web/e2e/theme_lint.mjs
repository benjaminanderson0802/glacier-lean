// Theme guard: retro art uses only palette tokens, integer pixel sizing, sprite frames and Press Start 2P.
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
  [/font-size\s*:\s*(?!0(?:\s|;|\})|var\(--g-size-(?:body|title)\)|calc\(\s*(?:8|16)\s*\*\s*var\(--px\)\s*\))[^;]+/gi, 'font-size outside the 8*--px body and 16*--px title scale'],
  [/font\s*:\s*(?!var\(--g-size-(?:body|title)\)|calc\(\s*(?:8|16)\s*\*\s*var\(--px\)\s*\))[^;]*var\(--g-font/g, 'font shorthand outside the 8*--px body and 16*--px title scale'],
  [/border-radius\s*:(?!\s*0\s*!important)/g, 'border radius is not allowed'],
  [/\b(?:<svg\b[^>]*>[\s\S]*?<\/svg>|<line\b|<path\b[^>]*(?:stroke|d=))/gi, 'inline SVG line icon (use a pixel sprite)'],
  [/box-shadow\s*:[^;]*(?:blur|\d+px\s+\d+px\s+\d+px)/gi, 'blurred box-shadow (use a solid pixel offset)'],
  [/fontFamily\s*:\s*['"`]/g, 'inline fontFamily not from tokens'],
  [/\b(Inter|Roboto|Helvetica|Arial|system-ui|-apple-system|Segoe UI|sans-serif)\b/g, 'generic UI font'],
  [/\bfonts\.googleapis|\bhttps?:\/\/(?!127\.0\.0\.1|localhost)[\w.-]+\.(com|net|io)\//g, 'remote asset (must be bundled for offline use)'],
]
const fails = []
for (const f of files) {
  if (f === TOKENS) continue
  const text = readFileSync(f, 'utf8')
  text.split('\n').forEach((line, i) => {
    if (/theme-lint-ignore/.test(line)) return
    const lintLine = line.replace(/border-radius\s*:\s*0(?:\s*!important)?/g, '').replace(/font-size\s*:\s*0(?:\s*[;}])/g, '')
    for (const [re, why] of rules) { re.lastIndex = 0; if (re.test(lintLine)) {
      const isScaleRule = why.startsWith('font-size outside') || why.startsWith('font shorthand outside')
      const variableSized = isScaleRule && /(?:font-size|font)\s*:\s*var\(--g-size-(?:body|title)\)/.test(lintLine)
      if (!variableSized) fails.push(`${path.relative(src, f)}:${i + 1}: ${why}\n    ${line.trim().slice(0, 140)}`)
    } }
  })
}
if (fails.length) { console.error(`THEME LINT FAILED (${fails.length})\n` + fails.join('\n')); process.exit(1) }
const css = readFileSync(path.join(src, 'theme/ui.css'), 'utf8')
if (!css.includes("border-image: url('./sprites/frame-light.png')") || !css.includes('image-rendering: pixelated')) {
  console.error('THEME LINT FAILED (sprite frames and pixel rendering must be enabled)'); process.exit(1)
}
if (!css.includes('border-radius: 0 !important') || !css.includes('box-shadow: none !important')) { console.error('THEME LINT FAILED (global pixel-square surfaces and solid shadows are required)'); process.exit(1) }
console.log(`theme lint ok (${files.length} files)`)
