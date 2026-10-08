// Start screen: a pixel night scene with snowy peaks over a lake, the title and a small menu.
// Drawn at low resolution on a canvas and scaled up with crisp pixels; colours come from theme tokens.
import { useEffect, useRef, useState } from 'react'
import { tok } from '../ui/tok.ts'
import { Icon, type IconName } from '../ui/Pixel.tsx'
import { t } from '../i18n/index.ts'

const W = 192, H = 120

function rng(seed: number) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2 ** 32 } }

function draw(c: HTMLCanvasElement) {
  const g = c.getContext('2d')!
  const C = {
    sky0: tok('--g-void'), sky1: tok('--g-bar'), sky2: tok('--g-bg'), far: tok('--g-line-dim'), mid: tok('--g-accent-dim'),
    near: tok('--g-line'), snow: tok('--g-head'), ice: tok('--g-accent'), star: tok('--g-text'), water: tok('--g-panel'),
  }
  const r = rng(7)
  // sky bands (dithered)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const t = y / (H * 0.62)
    const band = t < 0.33 ? C.sky0 : t < 0.66 ? ((x + y) % 2 && t > 0.5 ? C.sky2 : C.sky1) : C.sky2
    g.fillStyle = band; g.fillRect(x, y, 1, 1)
  }
  for (let i = 0; i < 70; i++) { g.fillStyle = C.star; g.fillRect(Math.floor(r() * W), Math.floor(r() * H * 0.45), 1, 1) }
  const horizon = Math.round(H * 0.68)
  // mountain ridges: lit left faces, shaded right faces, snow caps above a jagged snow line
  const kind: string[][] = Array.from({ length: H }, () => Array(W).fill(''))
  const ridge = (lit: string, shade: string, peaks: [number, number][], slope: number, capDepth: number) => {
    for (let x = 0; x < W; x++) {
      let h = 0, side = 0, peakH = 0
      for (const [px, ph] of peaks) {
        const v = ph - Math.abs(x - px) * slope
        if (v > h) { h = v; side = x < px ? 0 : 1; peakH = ph }
      }
      if (h <= 0) continue
      h += Math.floor(r() * 2)
      const top = horizon - Math.round(h)
      const snowY = horizon - Math.round(peakH) + capDepth + Math.floor(r() * 3) + (side ? 2 : 0)
      for (let y = Math.max(0, top); y < horizon; y++) {
        const snow = y < snowY || (y < snowY + 2 && (x + y) % 2 === 0)
        const col = snow ? (side ? C.ice : C.snow) : side ? shade : lit
        g.fillStyle = col; g.fillRect(x, y, 1, 1)
        kind[y][x] = snow ? 'snow' : 'rock'
      }
    }
  }
  ridge(C.far, C.sky1, [[18, 30], [66, 40], [118, 36], [172, 42]], 0.95, 6)
  ridge(C.mid, C.far, [[44, 56], [142, 62]], 0.85, 12)
  ridge(C.near, C.mid, [[96, 40], [186, 30], [4, 28]], 1.25, 7)
  // lake: dark mirrored reflection with ripples
  for (let y = horizon + 1; y < H; y++) for (let x = 0; x < W; x++) {
    const sy = horizon - (y - horizon)
    const k = sy >= 0 ? kind[sy][x] : ''
    const ripple = (y * 7 + Math.floor(x / 5) * 3) % 5 === 0
    g.fillStyle = ripple ? C.sky2 : k === 'snow' ? C.mid : k === 'rock' ? C.far : C.water
    g.fillRect(x, y, 1, 1)
  }
  g.fillStyle = C.ice; g.fillRect(0, horizon, W, 1)
}

const MENU: { label: string; icon: IconName; go: string }[] = [
  { label: t('splash.continueMenu'), icon: 'run', go: 'home' },
  { label: t('splash.newAutomation'), icon: 'plus', go: 'ask' },
  { label: t('splash.settings'), icon: 'settings', go: 'settings' },
  { label: t('splash.exit'), icon: 'close', go: 'exit' },
]

export function Splash({ onDone, version }: { onDone: (to: string) => void; version: string }) {
  const cv = useRef<HTMLCanvasElement>(null)
  const [sel, setSel] = useState(0)
  useEffect(() => { if (cv.current) draw(cv.current) }, [])
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') setSel(s => (s + 1) % MENU.length)
      else if (e.key === 'ArrowUp') setSel(s => (s + MENU.length - 1) % MENU.length)
      else if (e.key === 'Enter' || e.key === ' ') onDone(MENU[sel].go)
      else if (e.key === 'Escape') onDone('home')
      else return
      e.preventDefault()
    }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [sel, onDone])
  const now = new Date()
  return (
    <div className="g-splash" data-testid="splash">
      <canvas ref={cv} width={W} height={H} className="g-splash-art" />
      <div className="g-splash-title">
        <div className="g-splash-word">{t('splash.name')}</div>
      </div>
      <nav className="g-splash-menu g-panel">
        {MENU.map((m, i) => (
          <button key={m.label} className={`g-navitem${i === sel ? ' active' : ''}`} onMouseEnter={() => setSel(i)} onClick={() => onDone(m.go)} data-testid={`splash-${m.go}`}>
            <span style={{ display: 'flex', gap: 12, alignItems: 'center' }}><Icon name={m.icon} />{m.label}</span>
          </button>
        ))}
      </nav>
      <div className="g-splash-foot"><span>{t('splash.versionPrefix')}{version}</span><span>{t('splash.continue')}</span><span>{now.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} {now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span></div>
    </div>
  )
}
