// Pixel art drawn on a grid. Every colour is a theme token (var(--g-*)); no raw colours here.
// Each art is a list of equal-length rows; each character maps to a colour in its palette ('.' = empty).
import { t } from "../i18n/index.ts"

type Pal = Record<string, string>

function runs(rows: string[], pal: Pal) {
  const out: { x: number; y: number; w: number; c: string }[] = []
  rows.forEach((row, y) => {
    let x = 0
    while (x < row.length) {
      const ch = row[x]
      if (ch === '.' || !pal[ch]) { x++; continue }
      let w = 1
      while (row[x + w] === ch) w++
      out.push({ x, y, w, c: pal[ch] })
      x += w
    }
  })
  return out
}

export function PixelArt({ rows, pal, px, className, title }: { rows: string[]; pal: Pal; px: number; className?: string; title?: string }) {
  const w = Math.max(...rows.map(r => r.length)), h = rows.length
  return (
    <svg className={className} width={w * px} height={h * px} viewBox={`0 0 ${w} ${h}`} shapeRendering="crispEdges" role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      {runs(rows, pal).map((r, i) => <rect key={i} x={r.x} y={r.y} width={r.w} height={1} style={{ fill: r.c }} />)}
    </svg>
  )
}

// ---------- tab + UI icons (9x9, drawn in currentColor so they follow the tab's text colour) ----------
const ICONS: Record<string, string[]> = {
  home: [
    '....#....',
    '...###...',
    '..##.##..',
    '.##...##.',
    '#########',
    '.#.....#.',
    '.#.###.#.',
    '.#.#.#.#.',
    '.#######.',
  ],
  ask: [
    '.#######.',
    '#.......#',
    '#.#.#.#.#',
    '#.......#',
    '.####.##.',
    '....#.#..',
    '....##...',
    '.........',
    '.........',
  ],
  automations: [
    '###......',
    '#.#####..',
    '###...#..',
    '......#..',
    '......#..',
    '....#####',
    '....#...#',
    '....#####',
    '.........',
  ],
  memory: [
    '.######..',
    '.#....##.',
    '.#.##..#.',
    '.#.....#.',
    '.#.###.#.',
    '.#.....#.',
    '.#.###.#.',
    '.#.....#.',
    '.#######.',
  ],
  settings: [
    '....#....',
    '.#.###.#.',
    '..#####..',
    '.##...##.',
    '###...###',
    '.##...##.',
    '..#####..',
    '.#.###.#.',
    '....#....',
  ],
  note: [
    '#######..',
    '#.....##.',
    '#.###..#.',
    '#......#.',
    '#.####.#.',
    '#......#.',
    '#.###..#.',
    '#......#.',
    '########.',
  ],
  run: [
    '..#####..',
    '.#.....#.',
    '#..#....#',
    '#..##...#',
    '#..###..#',
    '#..##...#',
    '#..#....#',
    '.#.....#.',
    '..#####..',
  ],
  lock: ['..#####..', '.#.....#.', '.#.....#.', '#########', '#.......#', '#...#...#', '#...#...#', '#.......#', '#########'],
  plus: ['.........', '....#....', '....#....', '....#....', '.#######.', '....#....', '....#....', '....#....', '.........'],
  search: ['..###....', '.#...#...', '#.....#..', '#.....#..', '#.....#..', '.#...#...', '..####...', '......##.', '.......##'],
  send: ['#........', '###......', '#.###....', '#...###..', '#.....###', '#...###..', '#.###....', '###......', '#........'],
  min: ['.........', '.........', '.........', '.........', '.........', '.........', '.#######.', '.#######.', '.........'],
  close: ['#.......#', '.#.....#.', '..#...#..', '...#.#...', '....#....', '...#.#...', '..#...#..', '.#.....#.', '#.......#'],
}
export type IconName = keyof typeof ICONS

export function Icon({ name, px = 3, className }: { name: IconName; px?: number; className?: string }) {
  return <PixelArt rows={ICONS[name]} pal={{ '#': 'currentColor' }} px={px} className={`g-icon ${className ?? ''}`} />
}

// ---------- status icons (11x11, fixed colours from tokens) ----------

export type StatusKind = 'bad' | 'warn' | 'ok' | 'run' | 'idle'
export function StatusIcon({ kind }: { kind: StatusKind; px?: number }) {
  // Limbo: a soft status dot instead of pixel art. Title keeps the meaning for screen readers and hover.
  const title = kind === 'ok' ? t('pixel.done') : kind === 'warn' ? t('pixel.queued') : kind === 'run' ? t('pixel.running') : kind === 'idle' ? t('pixel.waiting') : t('pixel.needsYou')
  return <span className={`g-status l-dot l-dot-${kind}`} role="img" aria-label={title} title={title} />
}

// ---------- logo: two snowy peaks ----------
function mountains(): string[] {
  const W = 26, H = 15
  const peaks = [{ x: 9, h: 15 }, { x: 18, h: 11 }]
  const rows: string[][] = Array.from({ length: H }, () => Array(W).fill('.'))
  for (let x = 0; x < W; x++) {
    let best = -1, side = 0
    for (const p of peaks) {
      const hh = p.h - Math.abs(x - p.x) * 1.15
      if (hh > best) { best = hh; side = x <= p.x ? 0 : 1 }
    }
    const top = H - Math.round(best)
    for (let y = Math.max(0, top); y < H; y++) {
      const depth = y - top
      rows[y][x] = depth < 2 ? 'w' : depth < 3 && (x + y) % 2 === 0 ? 'w' : side === 0 ? 'a' : 'l'
    }
  }
  return rows.map(r => r.join(''))
}
const LOGO = mountains()
export function Logo({ px = 2 }: { px?: number }) {
  return <PixelArt rows={LOGO} pal={{ w: 'var(--g-head)', a: 'var(--g-accent)', l: 'var(--g-line)' }} px={px} className="g-logo" title={t('pixel.glacier')} />
}
