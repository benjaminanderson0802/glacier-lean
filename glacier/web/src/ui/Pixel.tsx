// Pixel art drawn on a grid. Every colour is a theme token (var(--g-*)); no raw colours here.
// Each art is a list of equal-length rows; each character maps to a colour in its palette ('.' = empty).

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
const DISC = [
  '...xxxxx...',
  '..xxxxxxx..',
  '.xxxxxxxxx.',
  'xxxxxxxxxxx',
  'xxxxxxxxxxx',
  'xxxxxxxxxxx',
  'xxxxxxxxxxx',
  'xxxxxxxxxxx',
  '.xxxxxxxxx.',
  '..xxxxxxx..',
  '...xxxxx...',
]
const overlay = (base: string[], top: string[]) => base.map((r, y) => r.split('').map((c, x) => (top[y]?.[x] && top[y][x] !== '.' ? top[y][x] : c)).join(''))
const BANG = ['...........', '...........', '.....o.....', '.....o.....', '.....o.....', '.....o.....', '.....o.....', '...........', '.....o.....', '...........', '...........']
const TICK = ['...........', '.........o.', '........oo.', '.......oo..', 'o.....oo...', 'oo...oo....', '.oo.oo.....', '..ooo......', '...o.......', '...........', '...........']
const QUEUE = [
  'xxxxxxxxxxx',
  'xooooooooox',
  'xoxxxxxxxox',
  'xoxoooooxox',
  'xoxoxxxoxox',
  'xoxoxxxoxox',
  'xoxoxxxoxox',
  'xoxoooooxox',
  'xoxxxxxxxox',
  'xooooooooox',
  'xxxxxxxxxxx',
]
const SPIN = overlay(DISC.map(r => r.replace(/x/g, 'x')), ['...........', '...........', '...........', '...ooooo...', '...o...o...', '...o.o.o...', '...o...o...', '...ooooo...', '...........', '...........', '...........'])

export type StatusKind = 'bad' | 'warn' | 'ok' | 'run' | 'idle'
export function StatusIcon({ kind, px = 3 }: { kind: StatusKind; px?: number }) {
  if (kind === 'ok') return <PixelArt rows={TICK} pal={{ o: 'var(--g-ok)' }} px={px} className="g-status" title="done" />
  if (kind === 'warn') return <PixelArt rows={QUEUE} pal={{ x: 'var(--g-warn)', o: 'var(--g-bg)' }} px={px} className="g-status" title="queued" />
  if (kind === 'run') return <PixelArt rows={SPIN} pal={{ x: 'var(--g-accent)', o: 'var(--g-panel)' }} px={px} className="g-status g-status-run" title="running" />
  if (kind === 'idle') return <PixelArt rows={DISC} pal={{ x: 'var(--g-line-dim)' }} px={px} className="g-status" title="waiting" />
  return <PixelArt rows={overlay(DISC, BANG)} pal={{ x: 'var(--g-bad)', o: 'var(--g-bad-ink)' }} px={px} className="g-status" title="needs you" />
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
  return <PixelArt rows={LOGO} pal={{ w: 'var(--g-head)', a: 'var(--g-accent)', l: 'var(--g-line)' }} px={px} className="g-logo" title="Glacier" />
}

// ---------- mascot: an original little operator with dark hair and a backpack ----------
const MASCOT = [
  '....hh.hhhh.hh....',
  '..hhhhhhhhhhhhhh..',
  '.hhhhHhhhhhhHhhhh.',
  'hhhhhhhhhhhhhhhhhh',
  'hhhhhhhhhhhhhhhhhh',
  'hhhsshhhhhhhhsshhh',
  '.hhsssssssssssshh.',
  '.hsseesssssseessh.',
  '.hssssssssssssssh.',
  '..sssssssmmsssss..',
  '...SSssssssssSS...',
  '.....wwwSSwww.....',
  '...bwwwwwwwwwwb...',
  '..bbwwwWwwWwwwbb..',
  '..bbswwWwwWwwsbb..',
  '...sswwwwwwwwss...',
  '.....pppppppp.....',
  '.....ppp..ppp.....',
  '....kkkk..kkkk....',
]
export function Mascot({ px = 4 }: { px?: number }) {
  return (
    <PixelArt rows={MASCOT} px={px} className="g-mascot" pal={{
      h: 'var(--g-art-hair)', H: 'var(--g-art-hair-hi)', s: 'var(--g-art-skin)', S: 'var(--g-art-skin-sh)',
      e: 'var(--g-art-ink)', m: 'var(--g-art-mouth)', w: 'var(--g-head)', W: 'var(--g-text)',
      b: 'var(--g-art-strap)', p: 'var(--g-art-pants)', k: 'var(--g-art-ink)',
    }} />
  )
}
