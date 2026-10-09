import { useEffect, useState } from 'react'
import { Icon, type IconName } from '../ui/Pixel.tsx'
import { t } from '../i18n/index.ts'
import './splash.css'

const MENU: { label: string; icon: IconName; go: string }[] = [
  { label: t('splash.continueMenu'), icon: 'run', go: 'home' },
  { label: t('splash.newAutomation'), icon: 'plus', go: 'ask' },
  { label: t('splash.settings'), icon: 'settings', go: 'settings' },
  { label: t('splash.exit'), icon: 'close', go: 'exit' },
]

export function Splash({ onDone, version }: { onDone: (to: string) => void; version: string }) {
  const [sel, setSel] = useState(0)
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
      <div className="g-splash-panel">
        <div className="g-splash-title">limbo</div>
        <nav className="g-splash-menu" aria-label="limbo">
          {MENU.map((m, i) => (
            <button key={m.label} className={`g-splash-item${i === sel ? ' active' : ''}`} onMouseEnter={() => setSel(i)} onClick={() => onDone(m.go)} data-testid={`splash-${m.go}`}>
              <Icon name={m.icon} />{m.label}
            </button>
          ))}
        </nav>
        <div className="g-splash-foot"><span>{t('splash.versionPrefix')}{version}</span><span>{t('splash.continue')}</span><span>{now.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} {now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span></div>
      </div>
    </div>
  )
}
