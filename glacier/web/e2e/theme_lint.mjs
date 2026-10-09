// Theme guard for the Limbo look: frosted glass panels in a painted room.
// Colours and fonts live only in src/theme/ (tokens.css and ui.css); screens use the tokens.
// Everything is bundled for offline use. The room painting and the glass shell must be present.
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const src = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src')
const THEME = path.join(src, 'theme')
const files = []
const walk = d => readdirSync(d).forEach(f => { const p = path.join(d, f); statSync(p).isDirectory() ? walk(p) : /\.(css|tsx?|mjs)$/.test(f) && files.push(p) })
walk(src)

const screenRules = [
  [/#[0-9a-fA-F]{3,8}\b(?![\w-]*['"]?\s*\])/g, 'raw hex colour (use a --g-* or --l-* token)'],
  [/\b(rgba?|hsla?|oklch|lab)\(/g, 'raw colour function (use a --g-* or --l-* token)'],
]
const everywhere = [
  [/font-family\s*:(?!\s*(var\(--g-font|inherit))/g, 'font-family not from tokens'],
  [/fontFamily\s*:\s*['"`]/g, 'inline fontFamily not from tokens'],
  [/\bfonts\.googleapis|\bhttps?:\/\/(?!127\.0\.0\.1|localhost)[\w.-]+\.(com|net|io)\//g, 'remote asset (must be bundled for offline use)'],
]
const fails = []
for (const f of files) {
  const inTheme = f.startsWith(THEME + path.sep)
  if (f === path.join(THEME, 'tokens.css')) continue
  readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
    if (/theme-lint-ignore/.test(line)) return
    for (const [re, why] of [...everywhere, ...(inTheme ? [] : screenRules)]) { re.lastIndex = 0; if (re.test(line)) fails.push(`${path.relative(src, f)}:${i + 1}: ${why}\n    ${line.trim().slice(0, 140)}`) }
  })
}
const css = readFileSync(path.join(THEME, 'ui.css'), 'utf8')
const need = [
  [existsSync(path.join(THEME, 'limbo/room.webp')), 'room painting theme/limbo/room.webp is missing'],
  [css.includes("url('./limbo/room.webp')"), 'the stage must paint the room'],
  [css.includes('backdrop-filter'), 'panels must be frosted glass (backdrop-filter)'],
  [/\.l-left\s*\{[^}]*rotateY\(/.test(css) && /\.l-right\s*\{[^}]*rotateY\(/.test(css), 'side panels must lie on the angled walls (rotateY)'],
  [existsSync(path.join(THEME, 'fonts/Nunito.woff2')), 'bundled Nunito font is missing'],
]
for (const [ok, why] of need) if (!ok) fails.push(`theme/ui.css: ${why}`)
if (fails.length) { console.error(`THEME LINT FAILED (${fails.length})\n` + fails.join('\n')); process.exit(1) }
console.log(`theme lint ok (${files.length} files)`)
